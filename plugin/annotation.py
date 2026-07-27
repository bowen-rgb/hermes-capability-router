"""Review-first annotation for discovery results.

Discovery is intentionally separate from this module.  It finds raw resources;
this module turns them into reviewable Capability metadata; only an approved
draft is persisted in the runtime Capability Registry.
"""

from __future__ import annotations

import re
from typing import Any

from .models import AnnotationDraft, Capability, Implementation
from .storage import CapabilityStore


class AnnotationReviewQueue:
    """Approves drafts explicitly before the runtime registry sees them."""

    def __init__(self, store: CapabilityStore) -> None:
        self._store = store

    def submit(self, draft: AnnotationDraft) -> str:
        """Persist discovered metadata for review, without activating it."""
        if draft.status != "pending_review":
            raise ValueError("Only pending drafts can enter the review queue.")
        return self._store.save_draft(draft)

    def approve(self, draft: AnnotationDraft) -> Capability:
        if draft.status not in {"pending_review", "approved"}:
            raise ValueError(f"Cannot approve a draft with status {draft.status!r}")
        self._store.upsert(draft.capability)
        return draft.capability

    def approve_by_id(self, draft_id: str) -> Capability:
        return self._store.approve_draft(draft_id)


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
                    "文字提取", "识别文字",
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
