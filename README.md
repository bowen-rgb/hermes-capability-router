# Hermes Capability Router Plugin

This repository contains a Hermes **general plugin**, not an MCP server.

Licensed under the [MIT License](LICENSE).

> **Language support:** the seeded routing vocabulary explicitly supports
> English, Chinese (中文), and French (français). The optional multilingual
> embedding backend also provides semantic matching across these languages.

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

## How it works

### Runtime routing lifecycle: the three routing layers

This path runs for a user request. The plugin enters through Hermes' public
`pre_llm_call` hook; it does not modify Hermes core.

```text
User request
  -> Plugin Hook
  -> 1. Scene Router       (large work area: vision / document / coding)
  -> 2. Semantic Router    (specific intent: OCR / image understanding)
  -> 3. Capability Resolver (find and rank a suitable implementation)
  -> routing guidance injected into Hermes
  -> Hermes selects or proposes an execution
  -> optional policy guard + outcome recording
```

The three-layer router tree:

```text
Router Runtime
├── Scene Router
│   └── vision | document | coding | ...
├── Semantic Router
│   └── text_extraction | image_understanding | ...
└── Capability Resolver
    ├── Capability Registry
    ├── Capability Index / local embedding search
    └── Implementation ranking
        └── Python package | CLI | API | MCP | local model | plugin/skill
```

Example requests:

```text
中文：把这张截图里的文字提取出来
Français : Extrais le texte de cette capture d'écran.
          -> vision -> text_extraction -> image_text_extraction

中文：这张图片里有什么？
Français : Qu'y a-t-il dans cette image ?
          -> vision -> image_understanding -> image_understanding
```

### Capability registration lifecycle: discovery and annotation

This is a separate background path. It decides what the plugin knows about;
it does not automatically activate an uncertain discovery.

```text
Installed or external source
  -> Discovery Engine
  -> Annotation Engine
  -> pending human review
  -> Capability Registry
  -> Capability Index
```

Its structure tree:

```text
Discovery & Annotation
├── Discovery Engine
│   ├── installed Hermes plugins
│   ├── Python packages
│   ├── CLI tools
│   ├── GitHub repositories and README metadata
│   ├── MCP tools
│   └── local models
└── Annotation Engine
    ├── metadata extraction
    ├── capability / scene / intent classification
    ├── multilingual tag generation
    ├── strengths and limitations
    └── persistent pending-review queue
```

`/capability-review` lists pending drafts in Hermes. Use
`/capability-review approve <number>` only after checking the source and its
actual availability on the machine.

## Embeddings: installation and configuration

Embeddings are optional: explicit Chinese, French, and English examples keep
working if the local model is unavailable. Install the embedding extra when you
want semantic matching for paraphrases and wording not listed in the examples.

On Windows, install into the same Python environment used by Hermes:

```powershell
$HermesPython = "$env:LOCALAPPDATA\hermes\hermes-agent\venv\Scripts\python.exe"
& $HermesPython -m pip install "sentence-transformers>=2.7,<3" "huggingface-hub>=0.34,<1.0"
```

Download the configured model once while online, then the plugin can operate
offline:

```powershell
& $HermesPython -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
```

After copying the plugin into Hermes, edit this **live configuration file**:

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\data\router-config.json
```

Key settings:

```json
{
  "embedding": {
    "model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "offline_only": true,
    "threshold": 0.42
  }
}
```

- `model`: local Sentence Transformers model identifier.
- `offline_only`: keep `true` after the model has been downloaded; set `false`
  temporarily only when intentionally allowing a download.
- `threshold`: minimum semantic similarity score. Increase it for stricter
  routing; decrease it carefully if paraphrases are not matched.

Restart the Gateway after changing this file.

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

The repository default is [router-config.json](plugin/data/router-config.json).
It controls the local embedding model, offline policy, semantic threshold, and
the environment-variable name used for GitHub authentication.  Do not put a
token in that file; the default token source is `GITHUB_TOKEN`.

## Hermes installation (after tests pass)

Copy the contents of `plugin/` to:

```text
%LOCALAPPDATA%\hermes\plugins\hermes-capability-router\
```

Restart Hermes and use `hermes plugins list` to confirm discovery.  The optional
strict guard remains disabled unless `HERMES_CAPABILITY_ROUTER_GUARD=1` is set.
