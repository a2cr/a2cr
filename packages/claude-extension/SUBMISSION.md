# A2CR Claude Directory Submission Notes

This note is the public-safe submission checklist for the A2CR Claude Desktop
Extension / MCPB package. It contains no reviewer credentials, API keys, local
client keys, recovery material, private WorkBaton content, or dashboard logs.

## Submission Target

- Connector type: Desktop extension / MCPB.
- Artifact: `a2cr-0.1.6.mcpb`.
- Public artifact URL:
  `https://github.com/a2cr/a2cr/releases/tag/v0.1.6`.
- Primary reason for MCPB: A2CR's WorkBaton privacy model depends on local
  validation and local encryption before upload. A remote MCP connector would
  change that boundary by receiving plaintext tool input on the server.
- Directory wording before approval: say "Claude Desktop MCPB" or "Claude
  Desktop Extension"; do not claim Anthropic Directory approval.

## Requirement Audit

| Requirement | Status | Evidence |
|---|---|---|
| MCPB manifest | Ready | `manifest.json` uses `manifest_version: 0.3`, Node entrypoint, public docs, support URL, icon, and platform/runtime compatibility. |
| Privacy policy in manifest | Ready | `manifest.json` includes `privacy_policies: ["https://a2cr.app/en/privacy"]`. |
| Privacy policy in README | Ready | `README.md` has a `Privacy Policy` section covering data collection, usage/storage, third-party sharing, retention, and contact. |
| Tool titles | Ready | Runtime MCP tool registration provides human-readable titles for all four MVP tools. |
| Tool annotations | Ready | Read-only tools set `readOnlyHint: true`; `save_context` sets `readOnlyHint: false` and `destructiveHint: true` because it can overwrite a named Slot. |
| Tool names | Ready | All MVP tool names are under the 64-character limit. |
| Sensitive configuration | Ready | `A2CR API Key` is declared as sensitive required user configuration. |
| Icon | Ready | `assets/icon.png` is a 512x512 PNG. |
| Reviewer setup path | Ready | `README.md` and `VERIFY.md` explain install and smoke steps with harmless test data. |
| Test credentials | Out-of-band | Provide a disposable A2CR reviewer account and API key in the submission form or a private reviewer channel only. |
| Working examples | Ready | See the three reviewer prompts in this file and the detailed smoke prompts in `VERIFY.md`. |
| MCP Inspector / Claude test | Pending final pre-submit run | `VERIFY.md` records Claude Desktop MCPB smoke coverage; run MCP Inspector or equivalent final protocol inspection immediately before form submission. |
| Allowed link URIs | Not used | The MCPB does not request `ui/open-link`; no allowlist is needed for the MVP tools. |
| MCP Apps screenshots | Not applicable | This is not an MCP App and does not surface interactive UI elements. |

## Current Tool Surface

| Tool | Behavior | Annotation |
|---|---|---|
| `get_account_limits` | Reads plan, quota, and policy metadata. | `readOnlyHint: true` |
| `list_contexts` | Lists WorkBaton Slot metadata only. | `readOnlyHint: true` |
| `save_context` | Validates and locally encrypts WorkBaton content, then saves ciphertext to A2CR. It can overwrite a named Slot. | `readOnlyHint: false`, `destructiveHint: true` |
| `load_context` | Loads a Slot and decrypts client-encrypted content locally. | `readOnlyHint: true` |

`save_context` can overwrite an existing named Slot, so it is marked
destructive for review safety. Dedicated delete tools are intentionally omitted
from the MVP MCPB until destructive action review is added.

## Reviewer Setup

Provide reviewer credentials outside the repository:

- A2CR test account email.
- A2CR test account password or magic-link flow details.
- A disposable A2CR API key for the reviewer.
- Confirmation that the test account contains no customer data, production
  secrets, private project data, or durable business records.
- Confirmation that the account is populated with at least one harmless
  disposable Slot so reviewers can list and load real metadata/content.

Reviewer smoke path:

1. Download `a2cr-0.1.6.mcpb` from the GitHub Release.
2. Install it in Claude Desktop through `Settings > Extensions > Advanced
   settings > Install Extension`.
3. Enter the disposable A2CR API key.
4. Keep `A2CR Base URL` as `https://a2cr.app`.
5. Run the read-only, save/load, and metadata smoke steps in `VERIFY.md`.

## Working Examples

Provide these prompts or close variants in the submission form. They use
harmless data and exercise every MVP tool.

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

## Known Limitations

- The first MCPB exposes the four WorkBaton MVP tools only.
- WorkStash MCPB parity is pending.
- Delete tools are intentionally omitted from the MCPB MVP.
- The MCPB is manually installed from GitHub Release until Anthropic Directory
  approval.
