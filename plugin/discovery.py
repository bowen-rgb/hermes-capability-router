"""Capability Discovery: find installed resources without changing routing.

The output is raw discovery records.  Pass those records to ``AnnotationEngine``
to create drafts, then use ``AnnotationReviewQueue`` to approve a capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
import shutil


@dataclass(frozen=True)
class DiscoveryRecord:
    source_type: str
    source_location: str
    name: str
    description: str = ""
    interface: str | None = None


class DiscoveryEngine:
    """Local-only discovery for already installed capability implementations."""

    def discover_hermes_plugins(self, directory: Path) -> tuple[DiscoveryRecord, ...]:
        if not directory.is_dir():
            return ()
        records: list[DiscoveryRecord] = []
        for child in sorted(directory.iterdir()):
            manifest = child / "plugin.yaml"
            if not child.is_dir() or not manifest.is_file():
                continue
            fields = self._simple_yaml_fields(manifest.read_text(encoding="utf-8", errors="replace"))
            records.append(
                DiscoveryRecord(
                    "plugin",
                    str(child),
                    fields.get("name", child.name),
                    fields.get("description", ""),
                    "plugin_hook",
                )
            )
        return tuple(records)

    def discover_python_packages(self, names: tuple[str, ...]) -> tuple[DiscoveryRecord, ...]:
        records: list[DiscoveryRecord] = []
        for name in names:
            try:
                package = metadata.metadata(name)
            except metadata.PackageNotFoundError:
                continue
            records.append(
                DiscoveryRecord(
                    "python_package",
                    name,
                    package.get("Name", name),
                    package.get("Summary", ""),
                    "python",
                )
            )
        return tuple(records)

    def discover_cli_tools(self, names: tuple[str, ...]) -> tuple[DiscoveryRecord, ...]:
        return tuple(
            DiscoveryRecord("cli", location, name, interface="command")
            for name in names
            if (location := shutil.which(name))
        )

    @staticmethod
    def _simple_yaml_fields(content: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in content.splitlines():
            if not line or line[0].isspace() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key in {"name", "description"}:
                fields[key] = value.strip().strip("'\"")
        return fields
