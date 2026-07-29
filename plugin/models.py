"""Stable capability-first data types used by the router."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Implementation:
    """One executable implementation of a capability."""

    implementation_id: str
    name: str
    type: str
    interface: str
    tool_names: tuple[str, ...] = ()
    source: str | None = None
    availability: str = "unknown"
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()


@dataclass(frozen=True)
class Capability:
    """A user-facing ability with one or more concrete implementations."""

    capability_id: str
    name: str
    description: str
    scenes: tuple[str, ...]
    intents: tuple[str, ...]
    tags: tuple[str, ...]
    implementations: tuple[Implementation, ...] = ()


@dataclass(frozen=True)
class AnnotationDraft:
    """A reviewable registration proposal produced by a discovery source."""

    source_type: str
    source_location: str
    capability: Capability
    confidence: float
    status: str = "pending_review"
    review_issues: tuple[tuple[str, str, str | None], ...] = ()
    review_note: str = ""


@dataclass(frozen=True)
class RouteDecision:
    scene: str | None
    intent: str | None
    capability: Capability | None
    implementation: Implementation | None
    confidence: float
    rationale: str

    def as_context(self) -> str:
        """Create short, factual guidance for Hermes' pre-LLM context hook."""
        if self.capability is None:
            return "[Capability Router] No confident capability route was found; use normal Hermes reasoning."
        implementation = self.implementation.name if self.implementation else "no installed implementation"
        tools = ", ".join(self.implementation.tool_names) if self.implementation else ""
        tool_note = f" Preferred Hermes tool(s): {tools}." if tools else ""
        return (
            "[Capability Router] "
            f"Scene={self.scene or 'unknown'}; intent={self.intent or 'unknown'}; "
            f"capability={self.capability.name}; preferred implementation={implementation}."
            f"{tool_note} Use this route when a tool is needed; do not substitute an unrelated implementation."
        )


def implementation_from_dict(value: dict[str, Any]) -> Implementation:
    return Implementation(
        implementation_id=value["implementation_id"],
        name=value["name"],
        type=value["type"],
        interface=value["interface"],
        tool_names=tuple(value.get("tool_names", [])),
        source=value.get("source"),
        availability=value.get("availability", "unknown"),
        strengths=tuple(value.get("strengths", [])),
        weaknesses=tuple(value.get("weaknesses", [])),
    )


def capability_from_dict(value: dict[str, Any]) -> Capability:
    return Capability(
        capability_id=value["capability_id"],
        name=value["name"],
        description=value["description"],
        scenes=tuple(value.get("scenes", [])),
        intents=tuple(value.get("intents", [])),
        tags=tuple(value.get("tags", [])),
        implementations=tuple(implementation_from_dict(item) for item in value.get("implementations", [])),
    )


def capability_to_dict(value: Capability) -> dict[str, Any]:
    return {
        "capability_id": value.capability_id,
        "name": value.name,
        "description": value.description,
        "scenes": list(value.scenes),
        "intents": list(value.intents),
        "tags": list(value.tags),
        "implementations": [
            {
                "implementation_id": item.implementation_id,
                "name": item.name,
                "type": item.type,
                "interface": item.interface,
                "tool_names": list(item.tool_names),
                "source": item.source,
                "availability": item.availability,
                "strengths": list(item.strengths),
                "weaknesses": list(item.weaknesses),
            }
            for item in value.implementations
        ],
    }
