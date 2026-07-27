"""Local capability and implementation registry storage.

This is intentionally separate from discovery and annotation.  Discovery
produces reviewable drafts; after approval, this store persists the validated
capability record used at runtime.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import AnnotationDraft, Capability, Implementation, capability_from_dict, capability_to_dict


class CapabilityStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS capabilities (
                    capability_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    scenes_json TEXT NOT NULL,
                    intents_json TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS implementations (
                    implementation_id TEXT PRIMARY KEY,
                    capability_id TEXT NOT NULL REFERENCES capabilities(capability_id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    interface TEXT NOT NULL,
                    tool_names_json TEXT NOT NULL,
                    source TEXT,
                    availability TEXT NOT NULL,
                    strengths_json TEXT NOT NULL,
                    weaknesses_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_implementations_capability
                    ON implementations(capability_id);
                CREATE TABLE IF NOT EXISTS annotation_drafts (
                    draft_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    source_location TEXT NOT NULL,
                    capability_json TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def upsert(self, capability: Capability) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO capabilities(capability_id, name, description, scenes_json, intents_json, tags_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(capability_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    scenes_json=excluded.scenes_json,
                    intents_json=excluded.intents_json,
                    tags_json=excluded.tags_json
                """,
                (
                    capability.capability_id,
                    capability.name,
                    capability.description,
                    json.dumps(capability.scenes),
                    json.dumps(capability.intents),
                    json.dumps(capability.tags),
                ),
            )
            connection.execute("DELETE FROM implementations WHERE capability_id = ?", (capability.capability_id,))
            connection.executemany(
                """
                INSERT INTO implementations(
                    implementation_id, capability_id, name, type, interface,
                    tool_names_json, source, availability, strengths_json, weaknesses_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        item.implementation_id,
                        capability.capability_id,
                        item.name,
                        item.type,
                        item.interface,
                        json.dumps(item.tool_names),
                        item.source,
                        item.availability,
                        json.dumps(item.strengths),
                        json.dumps(item.weaknesses),
                    )
                    for item in capability.implementations
                ],
            )

    def get(self, capability_id: str) -> Capability | None:
        self.initialize()
        with self._connect() as connection:
            record = connection.execute(
                "SELECT * FROM capabilities WHERE capability_id = ?", (capability_id,)
            ).fetchone()
            if record is None:
                return None
            implementations = connection.execute(
                "SELECT * FROM implementations WHERE capability_id = ? ORDER BY name", (capability_id,)
            ).fetchall()
        return Capability(
            capability_id=record["capability_id"],
            name=record["name"],
            description=record["description"],
            scenes=tuple(json.loads(record["scenes_json"])),
            intents=tuple(json.loads(record["intents_json"])),
            tags=tuple(json.loads(record["tags_json"])),
            implementations=tuple(self._implementation_from_row(row) for row in implementations),
        )

    def list(self) -> tuple[Capability, ...]:
        self.initialize()
        with self._connect() as connection:
            ids = [row[0] for row in connection.execute("SELECT capability_id FROM capabilities ORDER BY capability_id")]
        return tuple(item for capability_id in ids if (item := self.get(capability_id)) is not None)

    def save_draft(self, draft: AnnotationDraft) -> str:
        self.initialize()
        draft_id = f"{draft.source_type}:{draft.source_location}"
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO annotation_drafts(draft_id, source_type, source_location, capability_json, confidence, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(draft_id) DO UPDATE SET
                    capability_json=excluded.capability_json,
                    confidence=excluded.confidence,
                    status=CASE WHEN annotation_drafts.status='approved' THEN 'approved' ELSE excluded.status END
                """,
                (draft_id, draft.source_type, draft.source_location, json.dumps(capability_to_dict(draft.capability)), draft.confidence, draft.status),
            )
        return draft_id

    def list_drafts(self, status: str | None = None) -> tuple[tuple[str, AnnotationDraft], ...]:
        self.initialize()
        query = "SELECT * FROM annotation_drafts"
        values: tuple[str, ...] = ()
        if status:
            query += " WHERE status = ?"
            values = (status,)
        query += " ORDER BY created_at"
        with self._connect() as connection:
            rows = connection.execute(query, values).fetchall()
        return tuple(
            (
                row["draft_id"],
                AnnotationDraft(
                    row["source_type"],
                    row["source_location"],
                    capability_from_dict(json.loads(row["capability_json"])),
                    row["confidence"],
                    row["status"],
                ),
            )
            for row in rows
        )

    def approve_draft(self, draft_id: str) -> Capability:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM annotation_drafts WHERE draft_id = ?", (draft_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown annotation draft: {draft_id}")
            if row["status"] == "approved":
                capability = capability_from_dict(json.loads(row["capability_json"]))
            elif row["status"] != "pending_review":
                raise ValueError(f"Draft {draft_id!r} cannot be approved from {row['status']!r}")
            else:
                capability = capability_from_dict(json.loads(row["capability_json"]))
                connection.execute("UPDATE annotation_drafts SET status = 'approved' WHERE draft_id = ?", (draft_id,))
        self.upsert(capability)
        return capability

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _implementation_from_row(row: sqlite3.Row) -> Implementation:
        return Implementation(
            implementation_id=row["implementation_id"],
            name=row["name"],
            type=row["type"],
            interface=row["interface"],
            tool_names=tuple(json.loads(row["tool_names_json"])),
            source=row["source"],
            availability=row["availability"],
            strengths=tuple(json.loads(row["strengths_json"])),
            weaknesses=tuple(json.loads(row["weaknesses_json"])),
        )
