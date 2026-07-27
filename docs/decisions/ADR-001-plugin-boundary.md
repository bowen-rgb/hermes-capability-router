# ADR-001: Plugin-first, capability-first routing

## Decision

Build a general Hermes Python plugin.  Treat MCP as one implementation type,
not as the plugin's architecture or public entry point.

## Reason

A standalone MCP server is offered to the model like every other tool and is
not guaranteed to be selected.  Hermes plugins can inject context before the
LLM tool loop and veto inappropriate tool calls, which provides the closest
supported integration without changing Hermes core.

## Consequence

The project must not promise full deterministic tool replacement.  V1 provides
route guidance plus enforcement of explicit deny/allow policies.  A future
strict mode is conditional on a Hermes middleware/selection API.
