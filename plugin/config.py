"""Runtime configuration loaded from the deployable plugin bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_DEFAULTS: dict[str, Any] = {
    "embedding": {
        "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "offline_only": True,
        "threshold": 0.42,
    },
    "github": {"token_env": "GITHUB_TOKEN", "request_timeout_seconds": 15},
    "annotation": {"require_human_review": True},
}


def router_config() -> dict[str, Any]:
    path = Path(__file__).with_name("data") / "router-config.json"
    if not path.is_file():
        return _DEFAULTS
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return {
        **_DEFAULTS,
        **loaded,
        "embedding": {**_DEFAULTS["embedding"], **loaded.get("embedding", {})},
        "github": {**_DEFAULTS["github"], **loaded.get("github", {})},
        "annotation": {**_DEFAULTS["annotation"], **loaded.get("annotation", {})},
    }
