# A2CR WorkBaton Autonomous Save Specification

Last updated: 2026-05-08

Status: Draft for Stage 0 product scope freeze

This specification defines how an AI agent should autonomously decide to save a
WorkBaton checkpoint when a conversation becomes long, a task phase completes,
or context-window pressure appears.

The goal is not to make A2CR an autonomous orchestrator. The goal is to give
ordinary MCP-capable AI agents enough MCP-visible guidance to preserve useful
work state before the current window becomes fragile.

## Core Rule

WorkBaton autonomous save is allowed only through the local stdio A2CR MCP
wrapper because WorkBaton content must be encrypted locally before upload.

Remote MCP `save_context` remains disabled. A remote-only AI agent may explain
that the local stdio wrapper is required, but it must not send plaintext
WorkBaton content to the remote MCP surface.

## Success Criteria

An autonomous WorkBaton save flow is acceptable when:

- The AI agent can discover the behavior from MCP tool descriptions or
  `explain_a2cr_flows`.
- The AI can call `should_save_workbaton` when it is unsure whether an
  autonomous checkpoint is appropriate.
- The AI calls `get_account_limits` before automatic or large saves when the
  tool is available.
- The saved body contains compact `goal`, `current_state`, and `next_action`.
- The saved body excludes prohibited material.
- The saved body is encrypted by the local stdio wrapper before upload.
- The returned `user_facing_summary` is shown for routine in-thread saves; the
  full `resume_prompt` is shown or preserved when the user is switching windows
  or asks for it.
- The AI does not confuse WorkBaton with WorkThreads.

## Autonomous Save Triggers

The AI should consider saving WorkBaton when one or more of these is true:

- The conversation is getting long.
- The model context window or output quality appears to be under pressure.
- A coherent task phase is complete.
- A risky or difficult implementation step just succeeded.
- Tests, builds, smoke checks, or important manual checks just passed.
- The next concrete action is clear and should survive a new window.
- The user is about to switch tools, models, or windows.
- Work has resumed from an older WorkBaton and the state has materially changed.
- There is a blocker that another window or agent should continue from later.

The AI should prefer saving at stable boundaries, not after every small message.

## Do Not Save Triggers

The AI must not autonomously save when:

- The current content includes secrets, API keys, Authorization headers,
  cookies, private database URLs, service-role keys, `.env` contents, local
  client key material, or recovery key material.
- The AI would need to include customer data, personal data, payment data, or
  raw confidential business data to make the checkpoint useful.
- The only available content is a full transcript, long logs, generated caches,
  build artifacts, git diffs, or large source files.
- The AI is unsure which project or Slot should be overwritten.
- The user explicitly asked not to save.
- The AI only has the remote MCP surface and cannot use the local stdio wrapper
  for WorkBaton save.

When prohibited material is present, the AI should either omit it or ask the
user how to proceed. It must not save prohibited material to make the checkpoint
more complete.

## Required Save Body

Every autonomous save must include:

- `goal`: what the work is trying to accomplish.
- `current_state`: what is done, what changed, and what matters now.
- `next_action`: the concrete next step for a new AI window.

Recommended optional fields:

- `decisions`
- `constraints`
- `problems`
- `blockers`
- `failed_attempts`
- `references`
- `validation`
- `workspace_status`
- `previous_slot`
- `supersedes_slots`
- `latest_slot_hint`
- `completed_since_previous`
- `remaining_tasks_ordered`
- `do_not_use_slots`

Free/compact saves should keep optional fields short. Pro/detailed saves may
include more useful context, but Pro never permits secrets or sensitive data.

## Save Before Or After Asking The User

The AI may save without asking when:

- The user has configured A2CR MCP and is actively using A2CR for the work.
- The save is compact and clearly useful for continuation.
- The Slot target is already known from the current workflow.
- No prohibited material is needed.

The AI should ask before saving when:

- The Slot name is ambiguous.
- Saving would overwrite a named Slot and no `latest_slot_hint` or user
  instruction makes the overwrite obvious.
- The checkpoint would include sensitive business context even after removing
  explicit secrets.
- The AI is about to create a new Slot that may affect plan limits.

## Required Tool Order

Recommended autonomous save order:

1. Call `explain_a2cr_flows` if the agent is newly connected or unsure whether
   to use WorkBaton or WorkThreads.
2. Call `should_save_workbaton` when available if the save trigger or safety
   boundary is uncertain.
3. Call `get_account_limits` when available, especially before automatic,
   large, or detailed saves.
4. Build a compact WorkBaton body.
5. Call local stdio `save_context`.
6. Inspect the result for `user_facing_summary`, `resume_prompt`, `slot_name`,
   expiry, and token metadata.
7. Tell the user that the WorkBaton was saved using `user_facing_summary`.
   Provide the full resume prompt only when switching windows or when requested.

## Advisory Tool: should_save_workbaton

A2CR exposes a helper MCP tool that lets an AI ask for a policy decision before
saving. The tool is advisory; it does not save content.

Input:

```json
{
  "reason": "conversation_getting_long",
  "project": "a2cr",
  "recent_progress": "WorkThreads MVP plan was drafted",
  "next_action": "Implement response resolution",
  "context_pressure": "medium",
  "last_saved_slot": "a2cr-main",
  "known_slot_name": "a2cr-main"
}
```

Output:

```json
{
  "should_save": true,
  "can_save_here": true,
  "required_save_path": "local stdio A2CR MCP wrapper",
  "recommended_slot_name": "a2cr-main",
  "recommended_detail_level": "compact",
  "call_get_account_limits_first": true,
  "warnings": [
    "Do not save secrets or full transcripts",
    "Keep current_state and next_action compact"
  ]
}
```

This tool should remain advisory. The local stdio `save_context` tool is still
the only WorkBaton save path.

## MCP Self-Description Requirements

The MCP surface must keep these facts visible to ordinary AI agents:

- `explain_a2cr_flows` explains the Baton/Threads split.
- `should_save_workbaton` explains whether a compact checkpoint is appropriate
  and whether the current MCP surface can save it.
- `save_context` says when autonomous WorkBaton saves are appropriate.
- `save_context` says the local stdio wrapper encrypts before upload.
- Remote MCP `save_context` says it is disabled for WorkBaton save.
- `get_account_limits` says it should be used before automatic saves.
- Tool descriptions warn against direct HTTP endpoint guessing.
- Tool descriptions warn against secrets, full transcripts, long logs, and
  large source bodies.

## Acceptance Tests

Before relying on autonomous saves:

- MCP tool listing includes `explain_a2cr_flows`.
- MCP tool listing includes `should_save_workbaton`.
- `explain_a2cr_flows` documents WorkBaton as serial handoff.
- `explain_a2cr_flows` documents WorkThreads as collaboration, not Baton.
- `should_save_workbaton` distinguishes local stdio save capability from the
  remote MCP surface.
- Local stdio `save_context` description includes autonomous save triggers.
- Local stdio `save_context` encrypts content before upload.
- Remote MCP `save_context` rejects plaintext save attempts before auth or
  service calls.
- Tests assert that secret-like content is not echoed in errors.
- Agent guide repeats the same autonomous save triggers and prohibitions.

## Non-Goals

- Do not add server-side LLM judgment for whether to save.
- Do not wake sleeping AI windows.
- Do not create WorkThreads automatically from WorkBaton saves.
- Do not save every message.
- Do not treat WorkBaton as a durable project knowledge base.
- Do not bypass the local client-encryption boundary for convenience.
