# WorkBaton Zero-Knowledge Implementation Plan

Updated: 2026-05-06

Related design: `docs/superpowers/specs/2026-05-06-workbaton-zero-knowledge-design.md`

## Repository Handling

This plan file and related design/spec files are working documents. They do not need to be committed or pushed unless the user explicitly asks for publication.

## Scope

This plan covers WorkBaton only.

WorkThreads are intentionally out of scope because shared threads require separate key sharing, agent membership, invitation, and rotation rules.

## Assumptions

- Existing server-side Fernet encryption remains supported during migration.
- Existing slots are treated as `server` encrypted, not zero-knowledge.
- New client-encrypted WorkBaton slots must never send plaintext body content or decryption keys to the A2CR server.
- Dashboard APIs continue to expose metadata only.
- The first client-side key strategy should be local key file based because it is the smallest implementation step. Passphrase-based cross-device recovery can follow later.

## Success Criteria

- Server-side plaintext `content` save/load still works for backward compatibility.
- Client-encrypted save/load stores and returns ciphertext without server-side decrypt.
- MCP wrapper can save and resume a client-encrypted WorkBaton while presenting decrypted `content` to the AI client.
- Dashboard shows encryption mode metadata without exposing saved body content.
- Documentation clearly distinguishes `server-encrypted` from `client-encrypted / zero-knowledge WorkBaton`.

## Phase 1: Database Mode Metadata

### Work

Add migration columns for Web SaaS `public.contexts`:

- `encryption_mode text NOT NULL DEFAULT 'server'`
- `encryption_version integer NOT NULL DEFAULT 1`
- `encryption_metadata jsonb`

Update local SQLite model/migration equivalent:

- Add matching fields to `services.db.Context`.
- Extend `_migrate_slot_number` or add a new local migration helper so existing local databases get the new columns.

### Verify

- Existing tests create and migrate local `contexts` successfully.
- Existing Web schema tests still pass.
- Existing rows default to `server` mode.

## Phase 2: Request And Response Schemas

### Work

Add encrypted payload schemas in `models/schemas.py`:

- `EncryptedContentSchema`
- `EncryptionKeyWrapSchema` if needed for nested key metadata.

Extend save requests:

- `SaveRequest`
- `WebContextSaveRequest`

Rules:

- Accept exactly one of `content` or `encrypted_content`.
- `content` means existing `server` mode.
- `encrypted_content` means new `client` mode.
- Validate encrypted payload shape and size, but do not validate plaintext WorkBaton fields server-side for encrypted mode.

Extend load/resume responses:

- Include `encryption_mode`.
- Return `content` for `server` mode.
- Return `encrypted_content` for `client` mode.

### Verify

- Test `content` only is accepted.
- Test `encrypted_content` only is accepted.
- Test both fields is rejected.
- Test neither field is rejected.
- Test invalid encrypted payload is rejected.

## Phase 3: Web Context Service

### Work

Update `services/web_context.py`:

- On `content`, keep current server-side Fernet behavior.
- On `encrypted_content`, serialize and store encrypted payload directly.
- Store `encryption_mode = 'client'`.
- Store `encryption_metadata` from non-secret payload metadata.
- Avoid calling `encrypt()` or `decrypt()` for client-encrypted payloads.
- Keep rate limits, slot limits, retention, stats, and access logs unchanged.

Update `routers/web_context.py` response conversion helpers for the new response shape.

### Verify

- Existing Web Context tests pass.
- New client-encrypted save/load test confirms the returned payload matches stored ciphertext.
- New test confirms `decrypt()` is not called for client-encrypted load.
- Dashboard-related tests still confirm body content is not exposed by dashboard APIs.

## Phase 4: Local Prototype Context Service

### Work

Update `services/context.py` and `routers/context.py` with the same mode behavior:

- `content` saves use existing Fernet path.
- `encrypted_content` saves store ciphertext directly.
- `load_context` returns either plaintext content or encrypted payload according to mode.

Keep local behavior small and aligned with Web Context service.

### Verify

- Existing local context API tests pass.
- New local encrypted save/load roundtrip test passes.
- Existing MCP tests continue to pass in server mode before MCP encryption is enabled.

## Phase 5: MCP Wrapper Client Encryption

### Work

Update `mcp/server.py`:

- Add local key file creation/loading.
- Add client-side encrypt/decrypt helpers.
- Save WorkBaton content as `encrypted_content` by default when the local key is available.
- On load/resume:
  - If server mode, keep existing behavior.
  - If client mode, decrypt locally and return the same final shape MCP users already expect.

Key file MVP:

- Generate a random local key on first use.
- Store it outside the repository, under the user's local config directory.
- Never send the key to A2CR.
- Never print the key in tool responses or logs.

### Verify

- MCP save -> resume returns decrypted WorkBaton content to the AI client.
- API/database side receives only encrypted payload for client mode.
- If the key file is missing, load fails with a clear recoverability message instead of returning ciphertext as if it were usable.

## Phase 6: Dashboard Metadata

### Work

Update dashboard API and frontend metadata types:

- Include `encryption_mode` on context metadata.
- Show a small label such as `Server-encrypted` or `Client-encrypted`.
- Do not add body preview for client-encrypted content.

Likely files:

- `models/schemas.py`
- `services/dashboard.py`
- `routers/dashboard.py`
- `web/src/lib/types.ts`
- `web/src/pages/DashboardPage.tsx`

### Verify

- Dashboard API tests prove no body content is returned.
- Frontend build succeeds.
- Dashboard displays mode metadata without changing slot operations.

## Phase 7: Documentation

### Work

Update:

- `README.md`
- `SECURITY.md`
- `docs/runbooks/security.md`
- Optional: public guide copy if the feature is exposed publicly.

Required wording:

- Server-side Fernet mode is `application-layer encrypted` and `not zero-knowledge`.
- Client-encrypted WorkBaton may be described as zero-knowledge only for that mode.
- A2CR as a whole must not be described as zero-knowledge while WorkThreads and legacy server-encrypted slots exist.

### Verify

- Search for `zero-knowledge` and confirm claims are scoped.
- Search for `end-to-end` and confirm it is not overclaimed.
- Confirm docs explain key loss: A2CR cannot recover client-encrypted content without the client key.

## Recommended Order

1. Phase 1 and 2 together.
2. Phase 3 with tests.
3. Phase 4 with tests.
4. Phase 5 after server behavior is locked by tests.
5. Phase 6.
6. Phase 7.

This order keeps the server contract stable before adding MCP key handling.

## Open Decisions

- Whether MVP client encryption should be enabled by default in `mcp/server.py`, or introduced behind an environment flag first.
- Exact AEAD library and algorithm for Python local encryption.
- Local key file path and rotation story.
- Whether browser dashboard should ever create client-encrypted slots through WebCrypto, or whether zero-knowledge save/load should stay MCP-only for the first release.
