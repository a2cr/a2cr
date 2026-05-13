# A2CR WorkBaton Format

Status: early public specification draft

A2CR defines a portable handoff format for AI agents.

WorkBaton lets one AI session pass only the essential working state to the next:
goal, current state, decisions, blockers, validation, next action, and optional
references to supporting WorkStash notes.

Anyone may implement the WorkBaton Format. The official client and hosted relay
are maintained by A2CR.

## Scope

This specification area is for:

- WorkBaton field definitions
- WorkStash reference behavior
- MCP tool contracts for save, load, and resume
- security boundary notes
- examples and future conformance tests

It does not define the hosted A2CR backend, dashboard, billing, database schema,
or operations.

## Current Files

- `LICENSE.md` - license separation for specification text and machine-readable assets

Planned files:

- `workbaton-format.md`
- `workstash-reference.md`
- `mcp-tool-contract.md`
- `security-boundary.md`
- JSON Schema and conformance examples

## Compatibility Language

Allowed:

```text
Implements the WorkBaton Format.
Compatible with the WorkBaton Format.
```

Avoid unless you have written permission from A2CR:

```text
A2CR Certified.
Official A2CR Compatible.
```
