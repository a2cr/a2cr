# A2CR Claude Directory Submission Notes

This note is the public-safe submission checklist for the A2CR Claude Desktop
Extension / MCPB package. It contains no reviewer credentials, API keys, local
store files, recovery material, private WorkBaton or WorkStash content, or
dashboard logs.

## Submission Target

- Connector type: Desktop extension / MCPB.
- Artifact: `a2cr-0.1.7.mcpb`.
- Public artifact URL:
  `https://github.com/a2cr/a2cr/releases/tag/v0.1.7`.
- Primary reason for MCPB: A2CR's WorkBaton and WorkStash privacy model depends
  on local validation, local encryption, and local storage. A remote MCP
  connector would change that boundary by receiving plaintext tool input on the
  server.
- Directory wording before approval: say "Claude Desktop MCPB" or "Claude
  Desktop Extension"; do not claim Anthropic Directory approval.

## Requirement Audit

| Requirement | Status | Evidence |
|---|---|---|
| MCPB manifest | Ready | `manifest.json` uses `manifest_version: 0.3`, Node entrypoint, public docs, support URL, icon, and platform/runtime compatibility. |
| Privacy policy in manifest | Ready | `manifest.json` includes `privacy_policies: ["https://github.com/a2cr/a2cr/blob/main/docs/privacy.md"]`. |
| Privacy policy in README | Ready | `README.md` has a `Privacy Policy` section covering data collection, usage/storage, third-party sharing, retention, and contact. |
| Tool titles | Ready | Runtime MCP tool registration provides human-readable titles for all WorkBaton and WorkStash tools. |
| Tool annotations | Ready | Read-only tools set `readOnlyHint: true`; all tools set `openWorldHint: false`; `save_context`, `store_work_stash`, and `delete_work_stash` set `destructiveHint: true` because they can overwrite or delete local data. |
| Tool names | Ready | All tool names are under the 64-character limit. |
| Sensitive configuration | Ready | No hosted-service API key is required. The MCPB runs with local storage by default. |
| Icon | Ready | `assets/icon.png` is a 512x512 PNG. |
| Reviewer setup path | Ready | `README.md` and `VERIFY.md` explain install and smoke steps with harmless test data. |
| Test credentials | Not required | The local-only MCPB reviewer path does not require an A2CR account or API key. |
| Working examples | Ready | See the four reviewer prompts in this file and the detailed smoke prompts in `VERIFY.md`. |
| MCP protocol smoke | Ready | `tests/stdio-smoke.test.ts` starts the packaged Node MCP server over stdio and exercises all eight submitted tools with a temporary local store. |
| MCP Inspector / Claude Desktop manual install | Pending final pre-submit run | `VERIFY.md` records Claude Desktop MCPB smoke coverage; run MCP Inspector or Claude Desktop install verification immediately before submission. |
| Allowed link URIs | Not used | The MCPB does not request `ui/open-link`; no allowlist is needed for the submitted tools. |
| MCP Apps screenshots | Not applicable | This is not an MCP App and does not surface interactive UI elements. |

## Current Tool Surface

| Tool | Behavior | Annotation |
|---|---|---|
| `get_account_limits` | Reads local workspace limits and storage metadata. | `readOnlyHint: true`, `openWorldHint: false` |
| `list_contexts` | Lists WorkBaton Slot metadata only from the local store. | `readOnlyHint: true`, `openWorldHint: false` |
| `save_context` | Validates WorkBaton content, then saves it to the local store. It can overwrite a named Slot. | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |
| `load_context` | Loads a Slot and decrypts locally stored content. | `readOnlyHint: true`, `openWorldHint: false` |
| `store_work_stash` | Encrypts and stores a temporary supporting note in the local store. It can overwrite an existing entry key. | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |
| `get_work_stash` | Loads one referenced WorkStash entry and decrypts locally stored content. | `readOnlyHint: true`, `openWorldHint: false` |
| `list_work_stash` | Lists WorkStash metadata only; stored values are not returned. | `readOnlyHint: true`, `openWorldHint: false` |
| `delete_work_stash` | Deletes one local WorkStash entry. | `readOnlyHint: false`, `destructiveHint: true`, `openWorldHint: false` |

`save_context` can overwrite an existing named Slot, and `store_work_stash` can
overwrite an existing entry key, so both are marked destructive for review
safety. `delete_work_stash` is a dedicated destructive tool; no WorkBaton delete
tool is included in this MCPB submission.

## Reviewer Setup

No reviewer credentials are required for the local-only MCPB. Reviewers can
install the extension and create disposable local WorkBaton content during the
smoke test. WorkStash smoke data should also be disposable and clearly harmless.

Reviewer smoke path:

1. Download `a2cr-0.1.7.mcpb` from the GitHub Release.
2. Install it in Claude Desktop through `Settings > Extensions > Advanced
   settings > Install Extension`.
3. Run the read-only, WorkBaton save/load, WorkStash store/get/list/delete, and
   metadata smoke steps in `VERIFY.md`.

## Working Examples

Provide these prompts or close variants in the submission form. They use
harmless data and exercise every submitted tool.

1. Read account limits:

   ```text
   Use A2CR get_account_limits and summarize only the plan name, Slot limits,
   body size limit, and WorkStash limits. Do not save or delete anything.
   ```

2. Save and load a disposable WorkBaton:

   ```text
   Use A2CR save_context to save this harmless WorkBaton to
   "claude-mcpb-review-slot", then use load_context with the same slot_name and
   confirm the decrypted goal, current_state, next_action, blockers, and
   validation fields match.
   ```

3. List Slot metadata:

   ```text
   Use A2CR list_contexts. Confirm whether "claude-mcpb-review-slot" appears in
   Slot metadata. Do not print any WorkBaton body content.
   ```

4. Store, list, load, and delete a disposable WorkStash entry:

   ```text
   Use A2CR store_work_stash to save the value "temporary reviewer note" under
   entry_key "claude-mcpb-review-note" with tag "review". Then use
   list_work_stash with tag_filter "review" and confirm the stored value is not
   printed in metadata. Then use get_work_stash to load the value, and finally
   delete_work_stash for the same entry_key.
   ```

## Known Limitations

- The first MCPB exposes WorkBaton and WorkStash local tools only.
- WorkThreads MCPB parity is pending and intentionally excluded from this
  submission scope.
- No WorkBaton delete tool is included in the first MCPB submission.
- The MCPB is manually installed from GitHub Release until Anthropic Directory
  approval.

## Anthropic Automated Pickup Details

Send these details once after the `v0.1.7` GitHub Release has the MCPB asset and
checksum attached:

- `owner/repo`: `a2cr/a2cr`
- tag pattern: `v*` (example: `v0.1.7`)
- asset filename: `a2cr-<version>.mcpb`
- checksum filename: `SHA256SUMS.txt`
- maintainer contact: fill in the human contact before sending to Anthropic

The current release model is one cross-platform Node MCPB bundle for Claude
Desktop on macOS and Windows.
