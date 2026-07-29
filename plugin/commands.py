"""Human review commands exposed through Hermes plugin slash commands."""

from __future__ import annotations

from .annotation import AnnotationReviewQueue
from .storage import CapabilityStore
from .taxonomy import list_presets


_STATUS = {
    "pending_review": ("🟡", "待审核 / pending"),
    "needs_correction": ("🟠", "需要修正 / needs correction"),
    "approved": ("🟢", "已批准 / approved"),
    "rejected": ("🔴", "已拒绝 / rejected"),
}


def capability_review_command(store: CapabilityStore, queue: AnnotationReviewQueue, raw_args: str) -> str:
    """Review every discovery draft individually, with clear visual status.

    The command is deliberately simple enough to use inside a chat:
    ``approve``, ``reject``, ``set-tags``, ``apply-preset`` and ``mark-wrong``
    always take the visible draft number shown by the list command.
    """
    parts = raw_args.strip().split(maxsplit=2)
    action = parts[0].casefold() if parts else "list"
    drafts = store.list_drafts(None)

    if action in {"list", "all"}:
        return _render_list(drafts)
    if action == "pending":
        return _render_list(tuple(item for item in drafts if item[1].status in {"pending_review", "needs_correction"}))
    if action == "presets":
        return _render_presets()
    if action == "help":
        return _help()

    if len(parts) < 2 or not parts[1].isdigit():
        return _help()
    index = int(parts[1]) - 1
    if not 0 <= index < len(drafts):
        return "That review number does not exist. Run /capability-review first."
    draft_id, draft = drafts[index]
    detail = parts[2].strip() if len(parts) == 3 else ""

    try:
        if action == "approve":
            capability = queue.approve_by_id(draft_id)
            return f"🟢 Approved {capability.name}. It is now active in the Capability Registry."
        if action == "reject":
            queue.reject_by_id(draft_id, detail)
            return f"🔴 Rejected {draft.capability.name}. It remains visible in the review history."
        if action == "set-tags":
            tags = _parse_tags(detail)
            if not tags:
                return "Usage: /capability-review set-tags <number> tag one, tag two"
            updated = queue.edit_tags(draft_id, tags)
            return f"🟡 Updated tags for {updated.capability.name}. Review it again before approval."
        if action == "apply-preset":
            if not detail:
                return "Usage: /capability-review apply-preset <number> <preset-id>. Run /capability-review presets first."
            updated = queue.apply_preset(draft_id, detail)
            return f"🔵 Applied preset {updated.capability.capability_id} to {draft.capability.name}."
        if action == "mark-wrong":
            if not detail:
                return "Usage: /capability-review mark-wrong <number> <tag> [reason]"
            tag, _, note = detail.partition(" ")
            queue.flag_tag(draft_id, tag, note)
            return f"🟥 Marked tag '{tag}' as incorrect for {draft.capability.name}; this item now requires correction."
    except (KeyError, ValueError) as exc:
        return f"Review update failed: {exc}"
    return _help()


def _render_list(drafts) -> str:  # noqa: ANN001
    if not drafts:
        return "No annotation drafts yet. New discoveries will appear here for review."
    counts: dict[str, int] = {}
    for _, draft in drafts:
        counts[draft.status] = counts.get(draft.status, 0) + 1
    summary = " | ".join(f"{_STATUS[key][0]} {_STATUS[key][1]} {value}" for key, value in counts.items())
    lines = [f"Capability annotation review — {summary}", ""]
    for index, (_, draft) in enumerate(drafts, start=1):
        icon, label = _STATUS.get(draft.status, ("⚪", draft.status))
        capability = draft.capability
        lines.append(f"{icon} {index}. {capability.name} → `{capability.capability_id}` — {label}")
        lines.append(f"   tags: {' · '.join(f'`{tag}`' for tag in capability.tags) or '—'}")
        lines.append(f"   confidence: {draft.confidence:.0%} | source: {draft.source_location}")
        for severity, message, tag in draft.review_issues:
            marker = "🟥" if severity == "error" else "🟧"
            tag_note = f" [`{tag}`]" if tag else ""
            lines.append(f"   {marker}{tag_note} {message}")
        if draft.review_note:
            lines.append(f"   📝 reviewer note: {draft.review_note}")
        lines.append("")
    lines.append("Commands: approve | reject | set-tags | apply-preset | mark-wrong | presets | help")
    lines.append("Example: /capability-review mark-wrong 6 ocr This tool only understands images.")
    return "\n".join(lines)


def _render_presets() -> str:
    lines = ["🔵 Preset capability categories (choose one with apply-preset):"]
    for item in list_presets():
        lines.append(f"• `{item.capability_id}` — {item.description}")
    return "\n".join(lines)


def _parse_tags(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(tag.strip() for tag in value.split(",") if tag.strip()))


def _help() -> str:
    return "\n".join(
        (
            "Capability review commands:",
            "/capability-review                     list all drafts with coloured status",
            "/capability-review pending             list unresolved drafts only",
            "/capability-review approve <number>",
            "/capability-review reject <number> [reason]",
            "/capability-review set-tags <number> tag one, tag two",
            "/capability-review mark-wrong <number> <tag> [reason]",
            "/capability-review presets",
            "/capability-review apply-preset <number> <preset-id>",
        )
    )
