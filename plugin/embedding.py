"""Local, offline-first embeddings shared conceptually with Scope Recall."""

from __future__ import annotations

import os
from typing import Protocol

from .config import router_config


class EmbeddingBackend(Protocol):
    def similarities(self, query: str, candidates: tuple[str, ...]) -> tuple[float, ...]: ...


class LocalSentenceTransformerBackend:
    """Load the local Scope Recall model lazily and never download at runtime."""

    def __init__(
        self,
        model_name: str | None = None,
    ) -> None:
        self._model_name = model_name or router_config()["embedding"]["model"]
        self._model = None

    def similarities(self, query: str, candidates: tuple[str, ...]) -> tuple[float, ...]:
        model = self._load_model()
        vectors = model.encode([query, *candidates], normalize_embeddings=True)
        query_vector = vectors[0]
        return tuple(float(query_vector @ candidate) for candidate in vectors[1:])

    def _load_model(self):  # noqa: ANN202
        if self._model is not None:
            return self._model
        # sentence-transformers 2.x does not expose local_files_only.  These
        # standard offline flags make a missing cache fail safely instead of
        # downloading a model during a Hermes conversation.
        if router_config()["embedding"]["offline_only"]:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self._model_name, device="cpu")
        return self._model
