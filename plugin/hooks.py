"""Public-Hermes-hook integration for route guidance and audit logging."""

from __future__ import annotations

import logging
import os
import re
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

    def pre_llm_call(self, user_message: Any = "", **_: Any) -> dict[str, str] | None:
        text = user_message if isinstance(user_message, str) else str(user_message or "")
        if not text.strip():
            return None
        self._last_decision = self._resolver.route(text)
        context = self._last_decision.as_context()
        if note := self._discover_explicit_github_url(text):
            context = f"{context}\n{note}"
        return {"context": context}

    def _discover_explicit_github_url(self, text: str) -> str | None:
        """Network discovery happens only for a GitHub URL supplied by the user."""
        if self._review_queue is None:
            return None
        match = re.search(r"https?://github\.com/[\w.-]+/[\w.-]+", text, flags=re.IGNORECASE)
        if not match:
            return None
        url = match.group(0)
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
            return f"[Capability Discovery] Created pending-review annotation draft {draft_id} from the user-supplied GitHub repository. It is not active until approved."
        except Exception as exc:
            logger.warning("GitHub capability discovery failed for %s: %s", url, exc)
            return "[Capability Discovery] GitHub metadata could not be fetched; normal Hermes handling continues."

    def pre_tool_call(self, tool_name: str, **_: Any) -> dict[str, str] | None:
        """Optionally block a tool that conflicts with an explicit route.

        Disabled by default because Hermes' public hook cannot redirect a call.
        Operators can enable this conservative guard after registering accurate
        implementation tool names in the capability registry.
        """
        if os.getenv("HERMES_CAPABILITY_ROUTER_GUARD", "").lower() not in {"1", "true", "yes"}:
            return None
        decision = self._last_decision
        implementation = decision.implementation if decision else None
        if implementation and implementation.tool_names and tool_name not in implementation.tool_names:
            return {"action": "block", "message": f"Capability Router selected {implementation.name}; proposed tool {tool_name} conflicts with the active route."}
        return None

    def post_tool_call(self, tool_name: str, result: Any, **_: Any) -> None:
        logger.info("capability-router tool=%s routed=%s result_type=%s", tool_name, getattr(self._last_decision.capability, "capability_id", None) if self._last_decision else None, type(result).__name__)
