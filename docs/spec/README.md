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
- `workbaton-format.md` - WorkBaton v0.1 fields, rules, and examples
- `workstash-reference.md` - WorkStash entry model and reference behavior
- `mcp-tool-contract.md` - expected MCP tool behavior for save, load, resume, and stash operations
- `security-boundary.md` - encryption and trust boundary notes
- `VERSIONING.md` - versioning and breaking-change guidance
- `COMPATIBILITY.md` - compatibility wording and implementation baseline
- `EXTENSIONS.md` - extension field guidance
- `RFC_PROCESS.md` - lightweight process for proposing format changes
- `schema/workbaton.schema.json` - machine-readable WorkBaton v0.1 schema
- `schema/workstash.schema.json` - machine-readable WorkStash entry schema
- `examples/` - minimal and full examples for local implementers
- `conformance/README.md` - early conformance guidance

## Implementation Posture

This folder is intentionally implementation-level. These docs let a developer
build a local WorkBaton-compatible implementation without using the hosted A2CR backend.

The specification does not grant permission to use the A2CR name, logo, hosted
service, or official compatibility claims. Those boundaries are covered by
`TRADEMARK.md`, `NOTICE`, and the root `LICENSE`.

The public split is:

- anyone may implement the WorkBaton Format
- the official `a2cr-mcp` client is open source under Apache-2.0
- the legacy hosted A2CR relay, dashboard, billing, database, and operations are not included in this repository

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
