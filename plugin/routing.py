"""Third runtime layer: resolve a capability and its implementation."""

from __future__ import annotations

from .models import Capability, Implementation, RouteDecision
from .registry import CapabilityRegistry
from .semantic_router import SemanticRouter
from .scene_router import SceneRouter


class CapabilityResolver:
    """Use the registry, not hard-coded product names, to select capability."""

    def __init__(
        self,
        registry: CapabilityRegistry,
        scene_router: SceneRouter | None = None,
        semantic_router: SemanticRouter | None = None,
    ) -> None:
        self._registry = registry
        self._scene_router = scene_router or SceneRouter()
        self._semantic_router = semantic_router or SemanticRouter()

    def route(self, request: str) -> RouteDecision:
        scene_match = self._scene_router.route(request)
        scene = scene_match.scene
        intent_match = self._semantic_router.route(request, scene, self._registry.capabilities)

        ranked = [
            (self._score_capability(capability, scene, intent_match.intent), capability)
            for capability in self._registry.capabilities
        ]
        score, capability = max(ranked, default=(0.0, None), key=lambda item: item[0])
        if capability is None or score <= 0:
            return RouteDecision(None, None, None, None, 0.0, "No matching capability metadata.")

        implementation = self._choose_implementation(capability)
        confidence = min(
            (scene_match.confidence + intent_match.confidence + min(score / 5.0, 1.0)) / 3.0,
            1.0,
        )
        return RouteDecision(
            scene,
            intent_match.intent,
            capability,
            implementation,
            confidence,
            "Matched the Scene Router, Semantic Router, and capability metadata.",
        )

    @staticmethod
    def _score_capability(capability: Capability, scene: str | None, intent: str | None) -> float:
        score = 2.0 if scene and scene in capability.scenes else 0.0
        if intent and intent in capability.intents:
            score += 3.0
        return score

    @staticmethod
    def _choose_implementation(capability: Capability) -> Implementation | None:
        installed = [item for item in capability.implementations if item.availability == "installed"]
        return (installed or list(capability.implementations) or [None])[0]
