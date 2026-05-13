# Concepts

## WorkBaton

WorkBaton is a compact checkpoint for serial handoff from one AI window to the
next. It should contain only the state needed to resume:

- goal
- current state
- next action
- decisions
- blockers
- validation
- references to WorkStash entries when useful

## WorkStash

WorkStash is temporary supporting memory. It stores safe, concise notes that
would bloat a WorkBaton but may be useful to a future AI window.

WorkStash is not file storage, a durable knowledge base, or a secret manager.

## WorkThreads

WorkThreads are planned for multi-agent coordination. WorkBaton remains the
resume entrypoint for serial handoff.

## Project Memory Files

`AGENTS.md`, `CLAUDE.md`, and similar files are durable project guidance.
WorkBaton is current task state. They complement each other but do not replace
each other.
