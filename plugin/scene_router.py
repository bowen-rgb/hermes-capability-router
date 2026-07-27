"""First routing layer: determine the user's broad work scene."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SceneMatch:
    scene: str | None
    confidence: float


class SceneRouter:
    """Transparent V1 classifier, replaceable by a local embedding classifier."""

    _EXAMPLES = {
        "vision": (
            "图片", "截图", "图像", "屏幕", "画面",
            "image", "photo", "screen", "vision",
            "écran", "capture d'écran", "photo", "image",
        ),
        "document": (
            "pdf", "合同", "文档", "扫描件",
            "document", "contrat", "numérisé", "scan", "fichier",
        ),
        "coding": (
            "代码", "python", "github", "debug", "程序",
            "code", "débogage", "dépanner", "programme",
        ),
    }

    def route(self, request: str) -> SceneMatch:
        text = request.casefold()
        scores = {scene: sum(term in text for term in terms) for scene, terms in self._EXAMPLES.items()}
        scene, score = max(scores.items(), key=lambda item: item[1])
        return SceneMatch(scene if score else None, 1.0 if score else 0.0)
