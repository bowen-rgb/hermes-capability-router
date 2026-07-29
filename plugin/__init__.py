"""Hermes Capability Router Plugin.

This module deliberately uses only Hermes' public plugin context.  It does not
modify Hermes core or assume access to private tool-selection internals.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .annotation import AnnotationReviewQueue
from .commands import capability_review_command
from .hooks import CapabilityRouterHooks
from .registry import CapabilityRegistry
from .storage import CapabilityStore

logger = logging.getLogger(__name__)


def register(ctx) -> None:
    """Register public hooks, degrading safely if Hermes changes an API."""
    try:
        registry = CapabilityRegistry.from_default_file()
        store = CapabilityStore(Path(__file__).with_name("data") / "capability-registry.sqlite3")
        queue = AnnotationReviewQueue(store)
        hooks = CapabilityRouterHooks(registry, queue)
        for name, callback in (
            ("pre_llm_call", hooks.pre_llm_call),
            ("pre_tool_call", hooks.pre_tool_call),
            ("post_tool_call", hooks.post_tool_call),
        ):
            _register_hook(ctx, name, callback)
        _register_command(ctx, store, queue)
    except Exception:
        # Plugins are optional extensions.  Never let one make the gateway fail.
        logger.exception("Capability Router failed to initialize; Hermes continues without it")


def _register_hook(ctx, name: str, callback) -> None:  # noqa: ANN001
    ctx.register_hook(name, callback)


def _register_command(ctx, store: CapabilityStore, queue: AnnotationReviewQueue) -> None:
    callback = lambda raw_args: capability_review_command(store, queue, raw_args)
    try:
        ctx.register_command(
            "capability-review", callback,
            description="Review, correct, and approve discovered capability metadata.",
            args_hint="[pending|approve|reject|set-tags|apply-preset|mark-wrong|presets]",
        )
    except TypeError:
        # Older/newer Hermes builds may accept only name and callback.
        ctx.register_command("capability-review", callback)
