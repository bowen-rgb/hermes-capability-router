"""Read-only seed registry for the first verified plugin increment."""

from __future__ import annotations

import json
from pathlib import Path

from .models import Capability, capability_from_dict


class CapabilityRegistry:
    def __init__(self, capabilities: tuple[Capability, ...]) -> None:
        self._capabilities = capabilities

    @classmethod
    def from_default_file(cls) -> "CapabilityRegistry":
        source = Path(__file__).with_name("data") / "capabilities.json"
        raw = json.loads(source.read_text(encoding="utf-8"))
        return cls(tuple(capability_from_dict(item) for item in raw["capabilities"]))

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        return self._capabilities
