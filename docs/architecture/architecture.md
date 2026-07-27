# Hermes Capability Router Plugin

## Purpose

This project is a **Hermes Python plugin**, not an MCP server.  It helps Hermes
select relevant capabilities before a tool call is made, while keeping Hermes
core unchanged.

An MCP tool, CLI program, API, local model, package, skill, or another plugin
may be an *implementation* of a capability.  None of those is the product's
entry point.

## Verified Hermes boundary

Hermes Agent v0.19.0 provides plugin hooks including:

- `pre_llm_call`: injects routing guidance into the current turn.
- `pre_tool_call`: can allow or block a proposed tool call.
- `post_tool_call`: records outcomes for later ranking.

The public plugin interface does **not** expose a hook that replaces Hermes'
tool list or rewrites a proposed tool call into another one.  Therefore V1 is
an assisted-and-guarded router:

1. calculate a route before Hermes chooses a tool;
2. inject the selected scene, intent, and preferred implementation into context;
3. block calls that conflict with an explicit routing policy;
4. never claim that it can force a tool call when Hermes elects not to call any
   tool.

If strict mandatory routing becomes necessary, it requires a supported Hermes
middleware API or a small, separately maintained Hermes-core patch.

## Runtime routing lifecycle

```text
User request
  -> Hermes `pre_llm_call` plugin hook
  -> Scene Router
  -> Semantic Router
  -> Capability Resolver
  -> Capability Registry + Capability Index
  -> ranked implementation recommendation
  -> routing guidance injected into Hermes
  -> Hermes proposes a tool call (or responds directly)
  -> `pre_tool_call` policy guard allows or blocks it
  -> selected implementation executes
  -> `post_tool_call` records the outcome
```

## Capability registration lifecycle

```text
Installed or discovered source
  -> Discovery Engine
  -> Annotation Engine
  -> human review when confidence is insufficient
  -> Capability Registry
  -> Capability Index
```

Discovery and annotation are peer subsystems to routing and execution.  The
registry stores their validated output; it does not discover or annotate by
itself.

## Module tree

```text
Hermes Capability Router Plugin
├── Plugin Runtime
│   ├── hook integration
│   ├── route context store
│   └── routing-policy guard
├── Intelligence
│   ├── Scene Router
│   ├── Semantic Router
│   └── Capability Resolver
├── Capability Knowledge
│   ├── Capability Registry
│   ├── Implementation Registry
│   └── Capability Index
├── Discovery and Annotation
│   ├── Discovery Engine
│   ├── source parsers
│   ├── Annotation Engine
│   └── human-review queue
├── Execution Adapters
│   ├── MCP adapter
│   ├── CLI adapter
│   ├── API adapter
│   ├── Python-package adapter
│   ├── model adapter
│   └── plugin/skill adapter
└── Storage
    ├── metadata database
    ├── vector index
    └── outcome cache
```

## Core data model

`Capability` is the stable user-facing ability, such as `image_text_extraction`.

`Implementation` is a concrete way to provide it, such as PaddleOCR as a Python
package, a CLI command, an MCP tool, or a hosted API.  A capability can have many
implementations.  Each implementation records source, interface, availability,
requirements, strengths, weaknesses, cost, latency, and permissions.

## V1 scope

V1 will implement a local-only plugin with configurable scenes and intents,
manually seeded capabilities, route-context injection, and a conservative
`pre_tool_call` guard. Discovery, GitHub metadata enrichment, automated
annotation, and adapters will be added incrementally after the core route is
verified.
