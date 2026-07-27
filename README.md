# Hermes Capability Router Plugin

This repository contains a Hermes **general plugin**, not an MCP server.

Licensed under the [MIT License](LICENSE).

## Current V1 increment

- Reads seeded capability metadata.
- Routes a request to a scene, intent, capability, and preferred implementation.
- Injects the routing decision through Hermes' `pre_llm_call` hook.
- Optionally guards conflicting tool calls with `pre_tool_call`.
- Uses the same local multilingual embedding model configured for Scope Recall,
  with an offline-only loading policy and safe fallback.
- Discovers installed plugin/package/CLI resources and GitHub repository
  metadata/README content, then produces conservative,
  review-first capability-annotation drafts.

GitHub discovery uses the public GitHub REST API by default.  An optional
`ScraplingFetcher` adapter is available when Scrapling fetchers are installed.
Discovery does not automatically activate a guessed capability: it produces a
draft that must be reviewed before it enters the runtime registry.

For higher GitHub API limits or private repositories, set a fine-grained
personal access token in the `GITHUB_TOKEN` environment variable.  Public
repository discovery works without it; SSH and GPG keys are not used.

## Local development

Run the small routing test suite:

```powershell
python -m pytest
```

## Optional integrations

- The local embedding backend uses the same multilingual model configured for
  Scope Recall.  Keep `huggingface-hub>=0.34,<1.0` while Hermes uses
  `transformers 4.x`; `huggingface-hub 1.x` is incompatible with that runtime.
- GitHub repository discovery works with the public GitHub REST API by default.
  For pages that need HTML/browser extraction, install the optional adapter:

```powershell
python -m pip install ".\[scrapling]"
```

Discovery always creates a `pending_review` annotation draft; approval is the
only step that writes a capability into the runtime registry.

## Runtime configuration

The live plugin configuration is [router-config.json](plugin/data/router-config.json).
It controls the local embedding model, offline policy, semantic threshold, and
the environment-variable name used for GitHub authentication.  Do not put a
token in that file; the default token source is `GITHUB_TOKEN`.

## Hermes installation (after tests pass)

Copy the contents of `plugin/` to:

```text
%USERPROFILE%\.hermes\plugins\hermes-capability-router\
```

Restart Hermes and use `hermes plugins list` to confirm discovery.  The optional
strict guard remains disabled unless `HERMES_CAPABILITY_ROUTER_GUARD=1` is set.
