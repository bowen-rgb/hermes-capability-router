"""Optional GitHub repository discovery for the Annotation lifecycle.

The GitHub REST API is preferred for public repository metadata and README
content.  A Scrapling adapter can be supplied for pages that require HTML
extraction, but is not required for normal GitHub repository registration.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import os
from typing import Protocol
from urllib.request import Request, urlopen

from .config import router_config
from .discovery import DiscoveryRecord


class TextFetcher(Protocol):
    def get_text(self, url: str) -> str: ...


class UrllibFetcher:
    """Small dependency-free fetcher for public GitHub REST endpoints."""

    def get_text(self, url: str) -> str:
        config = router_config()["github"]
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "hermes-capability-router"}
        if token := os.getenv(config["token_env"]):
            headers["Authorization"] = f"Bearer {token}"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=config["request_timeout_seconds"]) as response:  # noqa: S310 - fixed public API endpoints from caller input
            return response.read().decode("utf-8", errors="replace")


class ScraplingFetcher:
    """Optional adapter.  It is activated only if Scrapling fetchers are installed."""

    def get_text(self, url: str) -> str:
        from scrapling.fetchers import Fetcher

        return Fetcher.get(url).text


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    repository: str

    @classmethod
    def parse(cls, url: str) -> "GitHubRepository":
        parts = url.rstrip("/").split("/")
        if len(parts) < 2 or "github.com" not in url.casefold():
            raise ValueError("Expected a GitHub repository URL.")
        return cls(parts[-2], parts[-1].removesuffix(".git"))


class GitHubDiscovery:
    def __init__(self, fetcher: TextFetcher | None = None) -> None:
        self._fetcher = fetcher or UrllibFetcher()

    def discover(self, repository_url: str) -> DiscoveryRecord:
        repo = GitHubRepository.parse(repository_url)
        metadata = json.loads(self._fetcher.get_text(f"https://api.github.com/repos/{repo.owner}/{repo.repository}"))
        readme = self._readme(repo)
        description = "\n".join(part for part in (metadata.get("description") or "", readme[:600]) if part).strip()
        return DiscoveryRecord(
            source_type="github_repository",
            source_location=repository_url,
            name=metadata.get("name") or repo.repository,
            description=description,
            interface="repository",
        )

    def _readme(self, repo: GitHubRepository) -> str:
        try:
            payload = json.loads(self._fetcher.get_text(f"https://api.github.com/repos/{repo.owner}/{repo.repository}/readme"))
            return base64.b64decode(payload.get("content", "")).decode("utf-8", errors="replace")
        except Exception:
            return ""
