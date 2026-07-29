# Changelog

## v0.1.5 — 2026-07-29

- Use SQLite WAL mode and a bounded busy timeout for the capability registry.
- Avoid repeated schema initialization in the plugin process.

## v0.1.4 — 2026-07-29

- Add per-item annotation review states, visible issue reasons, explicit
  incorrect-tag marking, manual tag edits, rejection history, and approval
  blocking while red issues remain.
- Add curated preset capability categories and portable emoji status colours
  for readable Hermes chat output.

## v0.1.3 — 2026-07-27

- Add transparent upstream acknowledgements and distinguish architecture
  references from optional dependencies and integrations.

## v0.1.2 — 2026-07-27

- Add Chinese and French README files, linked from the GitHub homepage.
- Document the multilingual routing approach and its regression-test policy.
- Expand explicit vocabulary for Traditional Chinese and French unaccented input.

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
