"""Second routing layer: determine user intent within the selected scene.

V1 uses readable examples.  Its interface is intentionally stable so a local
sentence-transformers backend can replace it later without changing hooks or
the Capability Registry.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging

from .embedding import EmbeddingBackend, LocalSentenceTransformerBackend
from .config import router_config
from .models import Capability

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntentMatch:
    intent: str | None
    confidence: float


class SemanticRouter:
    _EXAMPLES = {
        "text_extraction": ("提取文字", "提取这张", "识别文字", "图片文字", "截图文字", "截图里的文字", "ocr", "text extraction", "image to text"),
        "image_understanding": ("图片里有什么", "图片内容", "理解图片", "describe image", "image understanding"),
    }

    _PROTOTYPES = {
        "text_extraction": "Read or copy text from an image, screenshot, scanned document, OCR, 图片文字提取 识别截图文字",
        "image_understanding": "Understand, describe, or reason about what is in an image, 图片内容 图像理解",
    }

    def __init__(self, embedding_backend: EmbeddingBackend | None = None, embedding_threshold: float | None = None) -> None:
        self._embedding_backend = embedding_backend or LocalSentenceTransformerBackend()
        self._embedding_threshold = embedding_threshold if embedding_threshold is not None else router_config()["embedding"]["threshold"]
        self._embedding_available = True

    def route(self, request: str, scene: str | None, capabilities: tuple[Capability, ...]) -> IntentMatch:
        text = request.casefold()
        candidates = {
            intent
            for item in capabilities
            if scene is None or scene in item.scenes
            for intent in item.intents
        }
        scores = {
            intent: sum(example in text for example in self._EXAMPLES.get(intent, (intent.replace("_", " "),)))
            for intent in candidates
        }
        if not scores:
            return IntentMatch(None, 0.0)
        intent, score = max(scores.items(), key=lambda item: item[1])
        if score:
            return IntentMatch(intent, 1.0)
        return self._embedding_match(request, tuple(sorted(candidates)))

    def _embedding_match(self, request: str, candidates: tuple[str, ...]) -> IntentMatch:
        if not self._embedding_available:
            return IntentMatch(None, 0.0)
        try:
            similarities = self._embedding_backend.similarities(
                request,
                tuple(self._PROTOTYPES.get(intent, intent.replace("_", " ")) for intent in candidates),
            )
        except Exception as exc:  # Local model is optional; routing must survive its failure.
            self._embedding_available = False
            logger.warning("Capability Router embeddings unavailable; falling back to explicit examples: %s", exc)
            return IntentMatch(None, 0.0)
        best_index, best_score = max(enumerate(similarities), key=lambda item: item[1])
        if best_score < self._embedding_threshold:
            return IntentMatch(None, best_score)
        return IntentMatch(candidates[best_index], best_score)
