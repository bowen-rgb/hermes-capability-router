"""Review-first annotation for discovery results.

Discovery is intentionally separate from this module.  It finds raw resources;
this module turns them into reviewable Capability metadata; only an approved
draft is persisted in the runtime Capability Registry.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

from .models import AnnotationDraft, Capability, Implementation
from .storage import CapabilityStore
from .taxonomy import assess_capability, get_preset


class AnnotationReviewQueue:
    """Approves drafts explicitly before the runtime registry sees them."""

    def __init__(self, store: CapabilityStore) -> None:
        self._store = store

    def submit(self, draft: AnnotationDraft) -> str:
        """Persist discovered metadata for review, without activating it."""
        if draft.status != "pending_review":
            raise ValueError("Only pending drafts can enter the review queue.")
        return self._store.save_draft(self._assess(draft))

    def approve(self, draft: AnnotationDraft) -> Capability:
        if draft.status not in {"pending_review", "approved"}:
            raise ValueError(f"Cannot approve a draft with status {draft.status!r}")
        self._store.upsert(draft.capability)
        return draft.capability

    def approve_by_id(self, draft_id: str) -> Capability:
        draft = self._store.get_draft(draft_id)
        if any(severity == "error" for severity, _, _ in draft.review_issues):
            raise ValueError("Resolve or remove the red-tagged review issues before approval.")
        return self._store.approve_draft(draft_id)

    def edit_tags(self, draft_id: str, tags: tuple[str, ...]) -> AnnotationDraft:
        draft = self._store.get_draft(draft_id)
        capability = replace(draft.capability, tags=tags)
        return self._store.update_draft(draft_id, self._assess(replace(draft, capability=capability, status="pending_review")))

    def apply_preset(self, draft_id: str, preset_id: str) -> AnnotationDraft:
        preset = get_preset(preset_id)
        if preset is None:
            raise KeyError(f"Unknown preset category: {preset_id}")
        draft = self._store.get_draft(draft_id)
        capability = replace(
            draft.capability,
            capability_id=preset.capability_id,
            name=preset.name,
            description=preset.description,
            scenes=preset.scenes,
            intents=preset.intents,
            tags=preset.tags,
        )
        return self._store.update_draft(draft_id, self._assess(replace(draft, capability=capability, status="pending_review")))

    def flag_tag(self, draft_id: str, tag: str, note: str = "") -> AnnotationDraft:
        draft = self._store.get_draft(draft_id)
        issues = tuple(item for item in draft.review_issues if item[2] != tag)
        issues += (("error", note or f"Tag '{tag}' was marked incorrect by a reviewer.", tag),)
        return self._store.update_draft(
            draft_id, replace(draft, status="needs_correction", review_issues=issues, review_note=note or draft.review_note)
        )

    def reject_by_id(self, draft_id: str, note: str = "") -> AnnotationDraft:
        return self._store.reject_draft(draft_id, note)

    @staticmethod
    def _assess(draft: AnnotationDraft) -> AnnotationDraft:
        automatic = assess_capability(draft.capability, draft.confidence)
        current_tags = {tag.casefold() for tag in draft.capability.tags}
        manual = tuple(
            item for item in draft.review_issues
            if item[0] == "error"
            and "marked incorrect by a reviewer" in item[1]
            and item[2] is not None
            and item[2].casefold() in current_tags
        )
        issues = automatic + manual
        status = "needs_correction" if any(item[0] == "error" for item in issues) else "pending_review"
        return replace(draft, status=status, review_issues=issues)


class AnnotationEngine:
    """Conservative, local metadata annotator.

    V1 deliberately creates drafts rather than automatically activating an
    inferred capability.  This avoids an inaccurate tag causing Hermes to use
    the wrong implementation.  A future LLM annotator can implement the same
    ``annotate`` contract.
    """

    def annotate(
        self,
        *,
        source_type: str,
        source_location: str,
        name: str,
        description: str = "",
        interface: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AnnotationDraft:
        text = f"{name} {description}".casefold()
        details = metadata or {}
        if "paddleocr" in text or "tesseract" in text or "ocr" in text:
            capability = Capability(
                capability_id="vision.image_text_extraction",
                name="Image text extraction",
                description="Extract readable text from an image, screenshot, or scanned document.",
                scenes=("vision", "document"),
                intents=("text_extraction", "ocr"),
                tags=(
                    "ocr", "text extraction", "image to text",
                    "文字提取", "识别文字", "文字擷取", "辨識文字",
                    "extraction de texte", "reconnaissance de texte",
                ),
                implementations=(
                    Implementation(
                        implementation_id=self._identifier(name),
                        name=name,
                        type=source_type,
                        interface=interface or source_type,
                        source=source_location,
                        availability=details.get("availability", "installed"),
                        strengths=("OCR",),
                        weaknesses=("Does not perform general image reasoning",),
                    ),
                ),
            )
            return AnnotationDraft(source_type, source_location, capability, confidence=0.92)

        capability = Capability(
            capability_id=f"discovered.{self._identifier(name)}",
            name=name,
            description=description or f"Discovered {source_type} resource.",
            scenes=("general",),
            intents=("manual_review_required",),
            tags=(source_type, self._identifier(name)),
            implementations=(
                Implementation(
                    implementation_id=self._identifier(name),
                    name=name,
                    type=source_type,
                    interface=interface or source_type,
                    source=source_location,
                    availability=details.get("availability", "installed"),
                ),
            ),
        )
        return AnnotationDraft(source_type, source_location, capability, confidence=0.25)

    @staticmethod
    def _identifier(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-") or "resource"
