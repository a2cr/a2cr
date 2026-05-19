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

`A2CR.md`, `AGENTS.md`, `CLAUDE.md`, and similar files are durable project
guidance. A useful setup keeps detailed A2CR operating rules in `A2CR.md` and
adds a short pointer from the AI client's normal project memory file.

WorkBaton is current task state. Project memory files and WorkBaton complement
each other but do not replace each other.
