"""Human review commands exposed through Hermes plugin slash commands."""

from __future__ import annotations

from .annotation import AnnotationReviewQueue
from .storage import CapabilityStore


def capability_review_command(store: CapabilityStore, queue: AnnotationReviewQueue, raw_args: str) -> str:
    """List or approve pending annotation drafts.

    Usage in Hermes: ``/capability-review`` or
    ``/capability-review approve <number>``.
    """
    pending = store.list_drafts("pending_review")
    parts = raw_args.strip().split()
    if parts[:1] == ["approve"]:
        if len(parts) != 2 or not parts[1].isdigit():
            return "Usage: /capability-review approve <number>"
        index = int(parts[1]) - 1
        if not 0 <= index < len(pending):
            return "That pending-review number does not exist. Run /capability-review first."
        _, draft = pending[index]
        capability = queue.approve_by_id(pending[index][0])
        return f"Approved {capability.name} from {draft.source_location}. It is now in the Capability Registry."

    if not pending:
        return "No pending capability annotations."
    lines = ["Pending capability annotations:"]
    for index, (_, draft) in enumerate(pending, start=1):
        lines.append(
            f"{index}. {draft.capability.name} → {draft.capability.capability_id} "
            f"(confidence {draft.confidence:.2f}; source {draft.source_location})"
        )
    lines.append("Approve one with: /capability-review approve <number>")
    return "\n".join(lines)
