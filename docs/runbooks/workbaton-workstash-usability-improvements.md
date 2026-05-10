# WorkBaton And WorkStash Usability Improvement Notes

Last updated: 2026-05-09

Status: Reflected in MCP guidance, public docs, and save responses

This note captures hands-on feedback from using A2CR WorkBaton and WorkStash
during WorkThreads specification work. It is not a product promise; use it as a
scratchpad for later design and implementation cleanup.

## Reflected Changes

- `save_context` responses now support a concise `user_facing_summary` alongside
  the full `resume_prompt`.
- `should_save_workbaton` returns the exact deferred-tool search phrase,
  save-readiness guidance, WorkStash examples, and fresh-window guidance.
- A2CR flow explanations include a compact WorkBaton / WorkStash / no save /
  WorkThreads decision table.
- Usage docs and the A2CR agent skill include good and bad WorkStash examples.
- Agent guidance now includes context freshness heuristics and recommends
  showing full `resume_prompt` only when switching windows or when requested.

## What Worked Well

- `resume_context(slot_name=...)` restored enough state to continue without
  rereading the whole conversation.
- Compact WorkBaton fields such as `goal`, `current_state`, `next_action`,
  `decisions`, `remaining_tasks_ordered`, `validation`, and `workspace_status`
  were useful and well scoped.
- WorkStash worked well as supporting memory when the WorkBaton referenced a
  concrete `entry_key`.
- `should_save_workbaton` made autonomous save timing easier to justify.
- Safety warnings in `should_save_workbaton` and `save_context` helped keep
  secrets, long logs, diffs, generated caches, and source bodies out of saved
  context.
- Re-saving the same Slot after each settled spec decision was a good fit for
  iterative planning work.

## Friction Observed

- `save_context` was not visible at first. It appeared only after repeated
  `tool_search` queries for the exact tool name or related A2CR terms.
- The WorkBaton / WorkStash boundary is understandable after reading the tool
  descriptions, but a newly connected agent may still need examples for what to
  save in each place.
- `save_context` returns a `resume_prompt`, but normal in-thread work does not
  always need to show the full prompt to the user after every save.
- The recommended save flow is reliable but repetitive:
  `should_save_workbaton` -> `get_account_limits` -> `save_context`.
- WorkStash cleanup is mentioned in tool descriptions, but the user experience
  does not strongly surface when an entry should be deleted after a task phase is
  complete.
- There is no explicit agent behavior for detecting context drift or context
  contamination and nudging the user to continue in a fresh AI window after
  saving a WorkBaton.

## Improvement Ideas

- Carry the initial WorkStash quota decision into the implementation plan:
  Free 256KB total encrypted storage, Pro 2048KB total encrypted storage, with
  no public entry-count limit. Pro is larger because the same stash budget also
  supports Threads-related stash use. Entry count may remain an internal abuse
  guard, but public plan limits should be storage-based. These limits are
  deliberately modest so WorkStash remains temporary supporting memory rather
  than a file store or long-term project knowledge base.
- Make `save_context` easier to discover after `should_save_workbaton` returns
  `can_save_here=true`. Possible options:
  - ensure `save_context` becomes callable immediately after the advisory tool;
  - include the exact deferred-tool search phrase in the advisory result;
  - expose a short "save readiness" helper that confirms both limits and save
    capability.
- Add a compact decision table to A2CR docs and tool descriptions:
  - WorkBaton: compact resume checkpoint for a future window;
  - WorkStash: safe supporting note referenced by a WorkBaton;
  - no save: short task, no durable intermediate state;
  - WorkThreads: live shared coordination, not a Baton/Stash substitute.
- Add examples of good and bad WorkStash entries. Good examples are confirmed
  file paths, API behavior notes, reproduction details, and small decision
  summaries. Bad examples are secrets, API keys, auth headers, private DB URLs,
  full transcripts, long logs, diffs, generated caches, and large source bodies.
- Consider returning a concise `user_facing_summary` from `save_context`, separate
  from the full `resume_prompt`, so agents can report saves without cluttering
  the conversation.
- Consider adding a cleanup hint to `list_work_stash` or `save_context` when a
  retained WorkStash entry is likely no longer referenced by any active Baton.
- Add a "context freshness" behavior for agents. When an agent notices that the
  conversation context is becoming noisy, contradictory, stale, or polluted by
  old task state, it should:
  - call `should_save_workbaton`;
  - save a compact WorkBaton if recommended and possible;
  - tell the user that continuing in a fresh AI window would reduce context
    confusion;
  - provide the resume instruction or Slot name needed to continue;
  - avoid continuing risky implementation work in the polluted context unless the
    user explicitly asks to stay in the current window.
- Treat context contamination detection as heuristic, not perfect. The safer
  behavior is to catch early warning signs and suggest a fresh-window handoff
  before quality drops. Useful warning signs include:
  - older decisions conflicting with newer user instructions;
  - completed work being treated as unfinished;
  - assumptions from another task leaking into the current task;
  - uncertainty about which file, spec, branch, or goal is active;
  - stale conversation memory competing with current tool results;
  - repeated re-checking of the same facts because the active context feels
    unreliable;
  - the WorkBaton summary no longer matching the workspace state.
- Add proactive freshness triggers that do not require confirmed contamination:
  - a long task has passed through several distinct decisions or phases;
  - the user repeatedly says "next" through a multi-stage review;
  - edits span several documents or implementation areas;
  - the active task goal is no longer easy to state in one sentence;
  - a compact WorkBaton is becoming hard to keep compact.
- Keep `should_save_workbaton` advisory. The current explicit save step is useful
  because it gives the agent a final chance to keep the checkpoint compact and
  safe.

## Success Criteria For Later Changes

- A newly connected agent can discover and call the correct save tool without
  repeated searches.
- Agents can explain when to use WorkBaton, WorkStash, WorkThreads, or no save
  from MCP-provided information alone.
- Routine saves do not overwhelm the user with full resume prompts unless the
  user is switching windows or asks for the prompt.
- WorkStash entries are easy to reference from WorkBaton and easy to clean up
  after the task phase ends.
- Agents proactively suggest a fresh-window handoff when context contamination,
  stale assumptions, or accumulated unrelated task state could degrade quality.
