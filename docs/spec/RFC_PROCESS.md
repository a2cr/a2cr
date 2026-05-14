# Specification Change Process

Status: early public specification draft

For now, WorkBaton changes should stay lightweight. The goal is to gather real
agent-workflow feedback before creating heavy governance.

## Proposed Flow

1. Open a GitHub issue or discussion describing the problem.
2. Show at least one concrete handoff example.
3. Explain why existing fields or `extensions` are not enough.
4. Add or update examples and schema where relevant.
5. Keep the change optional unless a breaking version is planned.

## Review Questions

- Does this improve handoff continuity?
- Can a human understand it quickly?
- Does it encourage storing secrets, logs, transcripts, or large payloads?
- Can another implementation support it without using the hosted A2CR service?
- Is it general enough to belong in the format instead of an extension?
