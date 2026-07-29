"""Small, explicit capability taxonomy used by annotation review.

The taxonomy is intentionally curated rather than inferred at runtime.  It
gives reviewers predictable category choices and lets validation explain why a
generated tag looks suspicious.  The category families follow the broad task
groups commonly used by Hugging Face (vision, NLP, audio and multimodal), then
add practical agent categories such as code, web and automation.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import Capability


@dataclass(frozen=True)
class PresetCategory:
    capability_id: str
    name: str
    scenes: tuple[str, ...]
    intents: tuple[str, ...]
    tags: tuple[str, ...]
    description: str


PRESET_CATEGORIES: tuple[PresetCategory, ...] = (
    PresetCategory("vision.image_text_extraction", "Image text extraction", ("vision", "document"), ("text_extraction", "ocr"), ("ocr", "text extraction", "image to text"), "Read text from images, screenshots, scans, or PDFs."),
    PresetCategory("vision.image_understanding", "Image understanding", ("vision",), ("image_understanding", "visual_question_answering"), ("image understanding", "visual reasoning", "image description"), "Describe, compare, or reason about image content."),
    PresetCategory("document.parsing", "Document parsing", ("document",), ("document_parsing", "structured_extraction"), ("document", "pdf", "structured extraction"), "Extract structured data and layout from documents."),
    PresetCategory("text.translation", "Translation", ("translation", "text"), ("translation",), ("translation", "localization", "language"), "Translate text while preserving meaning and terminology."),
    PresetCategory("text.summarization", "Summarization", ("research", "text"), ("summarization",), ("summary", "summarization", "key points"), "Condense content into a concise summary."),
    PresetCategory("text.retrieval", "Knowledge retrieval", ("research", "knowledge"), ("retrieval", "search"), ("search", "retrieval", "knowledge base"), "Find relevant information in a knowledge source."),
    PresetCategory("code.development", "Software development", ("coding",), ("code_generation", "debugging", "refactoring"), ("code", "programming", "debugging"), "Write, inspect, test, or change software."),
    PresetCategory("web.research", "Web research", ("research", "web"), ("web_research", "web_search"), ("web", "research", "browser"), "Find and evaluate information on the web."),
    PresetCategory("data.analysis", "Data analysis", ("data", "research"), ("data_analysis",), ("data", "analysis", "dataset"), "Inspect, transform, and analyze structured data."),
    PresetCategory("audio.speech_to_text", "Speech to text", ("audio",), ("speech_to_text", "transcription"), ("audio", "transcription", "speech recognition"), "Transcribe spoken audio into text."),
    PresetCategory("audio.text_to_speech", "Text to speech", ("audio",), ("text_to_speech",), ("audio", "speech synthesis", "voice"), "Generate spoken audio from text."),
    PresetCategory("automation.workflow", "Workflow automation", ("automation",), ("automation", "workflow"), ("automation", "workflow", "integration"), "Automate repeatable actions across tools and services."),
)

_BY_ID = {item.capability_id: item for item in PRESET_CATEGORIES}


def get_preset(capability_id: str) -> PresetCategory | None:
    return _BY_ID.get(capability_id)


def list_presets() -> tuple[PresetCategory, ...]:
    return PRESET_CATEGORIES


def assess_capability(capability: Capability, confidence: float) -> tuple[tuple[str, str, str | None], ...]:
    """Return ``(severity, message, tag)`` review issues.

    These are *review hints*, not automatic rejections.  They intentionally
    flag only clear incomplete or contradictory metadata.
    """
    issues: list[tuple[str, str, str | None]] = []
    preset = get_preset(capability.capability_id)
    if confidence < 0.60:
        issues.append(("warning", "Low annotation confidence; verify the suggested category and tags.", None))
    if not capability.implementations:
        issues.append(("error", "No executable implementation was detected.", None))
    if not capability.scenes:
        issues.append(("error", "No scene is assigned.", None))
    if not capability.intents:
        issues.append(("error", "No intent is assigned.", None))
    if not capability.tags:
        issues.append(("error", "No tags are assigned.", None))
    if preset is None and capability.capability_id.startswith("discovered."):
        issues.append(("warning", "No preset category matched; choose a category or keep this as a custom capability.", None))
    if preset is not None:
        tags = {tag.casefold() for tag in capability.tags}
        conflicting = {
            "vision.image_text_extraction": {"image understanding", "visual reasoning", "image description"},
            "vision.image_understanding": {"ocr", "text extraction", "image to text"},
        }.get(preset.capability_id, set())
        for tag in sorted(tags & conflicting):
            issues.append(("warning", f"Tag '{tag}' conflicts with preset '{preset.name}'.", tag))
    return tuple(issues)
