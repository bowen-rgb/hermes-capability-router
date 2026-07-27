"""Hermes Capability Router Plugin.

This module deliberately uses only Hermes' public plugin context.  It does not
modify Hermes core or assume access to private tool-selection internals.
"""

from __future__ import annotations

from pathlib import Path

from .annotation import AnnotationReviewQueue
from .commands import capability_review_command
from .hooks import CapabilityRouterHooks
from .registry import CapabilityRegistry
from .storage import CapabilityStore


def register(ctx) -> None:
    """Register the supported lifecycle hooks with Hermes."""
    registry = CapabilityRegistry.from_default_file()
    store = CapabilityStore(Path(__file__).with_name("data") / "capability-registry.sqlite3")
    queue = AnnotationReviewQueue(store)
    hooks = CapabilityRouterHooks(registry, queue)
    ctx.register_hook("pre_llm_call", hooks.pre_llm_call)
    ctx.register_hook("pre_tool_call", hooks.pre_tool_call)
    ctx.register_hook("post_tool_call", hooks.post_tool_call)
    ctx.register_command(
        "capability-review",
        lambda raw_args: capability_review_command(store, queue, raw_args),
        description="List or approve pending capability annotations.",
        args_hint="[approve <number>]",
    )
