# WorkBaton Versioning

Status: early public specification draft

The current public format is WorkBaton Format v0.1.

## v0.1 Rules

Version v0.1 is intentionally small. Implementations should treat the required
fields as the portable minimum:

- `goal`
- `current_state`
- `next_action`

Optional fields may be added without breaking v0.1 consumers. A consumer should
ignore unknown fields unless it explicitly understands them.

## Compatibility Direction

The format should evolve toward:

- stable required fields
- optional additive fields
- JSON Schema validation
- clear security boundaries
- conformance examples before strict certification language

## Breaking Changes

A breaking change is any change that makes a valid v0.1 WorkBaton invalid or
changes the meaning of a required field.

Breaking changes should wait for a new major format version.
