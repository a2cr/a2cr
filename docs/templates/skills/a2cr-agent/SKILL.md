---
name: a2cr-agent
description: Use A2CR MCP for WorkBaton checkpoints and WorkThreads shared work coordination across AI windows, AI clients, and agents. Trigger when saving, resuming, loading, or coordinating AI work context through A2CR.
---

# A2CR Agent Workflow

Use A2CR as the shared context layer for AI-agent work. Prefer A2CR MCP tools over guessed HTTP endpoints unless the user explicitly asks for API integration work.

## Resume WorkBaton

When the user provides an A2CR resume prompt:

1. Call `resume_context(slot_name="...")` first.
2. Use `resume_context(slot_number=N)` only when the prompt says Slot numbers are supported.
3. If multiple candidates are returned, show the candidates and ask which one to load.
4. After loading, inspect the referenced project files as needed.
5. Treat current files and current user instructions as newer than saved context.
6. Continue in the language of the user's current message.

Do not invent missing facts when a slot is not found or expired.

## Save WorkBaton

When saving context, include the minimum information needed for the next AI window to resume:

- `goal`
- `current_state`
- `next_action`
- important decisions, constraints, risks, blockers, failed attempts, and references

Keep Free saves compact. For Pro detailed saves, include useful rationale, test results, failed attempts, and file responsibility notes when they improve resume quality.

Never save secrets, API keys, Authorization headers, private database URLs, personal data, full transcripts, long logs, generated caches, or large code bodies that can be read from the repository.

## Use WorkThreads

Use WorkThreads for active cross-agent coordination, not casual AI chat.

- Append concise work notes, review results, failures, decisions, and final result links.
- Check updates at task boundaries with `check_workthread_updates`.
- Use `wait_workthread_updates` only when waiting for another active agent.
- Do not assume A2CR can wake a stopped or sleeping AI window.
- Keep message bodies secret-safe and useful for another agent.

## If A2CR MCP Is Unavailable

Tell the user that the A2CR MCP tool is not available in the current client. Do not guess direct API calls or ask for secrets in chat.
