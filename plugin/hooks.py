"""Public-Hermes-hook integration for route guidance and audit logging."""

from __future__ import annotations

import logging
import os
import re
import threading
from typing import Any

from .annotation import AnnotationEngine, AnnotationReviewQueue
from .github_discovery import GitHubDiscovery
from .models import RouteDecision
from .registry import CapabilityRegistry
from .routing import CapabilityResolver

logger = logging.getLogger(__name__)


class CapabilityRouterHooks:
    def __init__(self, registry: CapabilityRegistry, review_queue: AnnotationReviewQueue | None = None) -> None:
        self._resolver = CapabilityResolver(registry)
        self._last_decision: RouteDecision | None = None
        self._review_queue = review_queue
        self._annotation_engine = AnnotationEngine()
        self._discovery_lock = threading.Lock()
        self._discovering_urls: set[str] = set()

    def pre_llm_call(self, user_message: Any = "", **_: Any) -> dict[str, str] | None:
        try:
            text = user_message if isinstance(user_message, str) else str(user_message or "")
        except Exception:
            return None
        if not text.strip():
            return None
        try:
            self._last_decision = self._resolver.route(text)
            context = self._last_decision.as_context()
            if note := self._queue_explicit_github_discovery(text):
                context = f"{context}\n{note}"
            return {"context": context}
        except Exception:
            # A routing hint must never prevent Hermes from handling a message.
            logger.exception("capability-router pre_llm_call failed; continuing without route guidance")
            return None

    def _queue_explicit_github_discovery(self, text: str) -> str | None:
        """Queue user-requested discovery without blocking the gateway event loop."""
        if self._review_queue is None:
            return None
        match = re.search(r"https?://github\.com/[\w.-]+/[\w.-]+", text, flags=re.IGNORECASE)
        if not match:
            return None
        url = match.group(0)
        with self._discovery_lock:
            if url in self._discovering_urls:
                return "[Capability Discovery] GitHub metadata discovery is already running for this repository."
            self._discovering_urls.add(url)
        threading.Thread(target=self._discover_github, args=(url,), name="capability-router-discovery", daemon=True).start()
        return "[Capability Discovery] GitHub metadata discovery was queued; it will appear in /capability-review when ready."

    def _discover_github(self, url: str) -> None:
        try:
            record = GitHubDiscovery().discover(url)
            draft = self._annotation_engine.annotate(
                source_type=record.source_type,
                source_location=record.source_location,
                name=record.name,
                description=record.description,
                interface=record.interface,
            )
            draft_id = self._review_queue.submit(draft)
            logger.info("Created pending-review capability draft %s from %s", draft_id, url)
        except Exception as exc:
            logger.warning("GitHub capability discovery failed for %s: %s", url, exc)
        finally:
            with self._discovery_lock:
                self._discovering_urls.discard(url)

    def pre_tool_call(self, tool_name: str, **_: Any) -> dict[str, str] | None:
        """Optionally block a tool that conflicts with an explicit route.

        Disabled by default because Hermes' public hook cannot redirect a call.
        Operators can enable this conservative guard after registering accurate
        implementation tool names in the capability registry.
        """
        try:
            if os.getenv("HERMES_CAPABILITY_ROUTER_GUARD", "").lower() not in {"1", "true", "yes"}:
                return None
            decision = self._last_decision
            implementation = decision.implementation if decision else None
            if implementation and implementation.tool_names and tool_name not in implementation.tool_names:
                return {"action": "block", "message": f"Capability Router selected {implementation.name}; proposed tool {tool_name} conflicts with the active route."}
        except Exception:
            logger.exception("capability-router pre_tool_call failed; allowing Hermes tool call")
        return None

    def post_tool_call(self, tool_name: str, result: Any, **_: Any) -> None:
        try:
            logger.info("capability-router tool=%s routed=%s result_type=%s", tool_name, getattr(self._last_decision.capability, "capability_id", None) if self._last_decision else None, type(result).__name__)
        except Exception:
            logger.exception("capability-router post_tool_call failed")
