# Changelog

## v0.1.1 — 2026-07-27

- Add explicit Chinese and French scene, intent, and annotation vocabulary.
- Document local embedding installation, download, and live configuration.
- Add both lifecycle diagrams and structure trees to the GitHub README.

## v0.1.0 — 2026-07-27

Initial public release of the Hermes Capability Router Plugin.

- Plugin-first Scene → Semantic → Capability routing guidance.
- Local multilingual embedding matching with an offline-safe fallback.
- Capability registry, implementation metadata, and persistent review queue.
- Discovery for installed plugins, selected Python packages, CLI tools, and
  GitHub repositories.
- Review-first annotation flow, including `/capability-review` commands.
- GitHub discovery through the REST API, with optional Scrapling fetchers.
- Centralized non-secret runtime configuration in `plugin/data/router-config.json`.
