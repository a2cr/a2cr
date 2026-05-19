# A2CR Security Checklist

This checklist is for low-cost security hygiene before and after public release.
It covers the public repository, the official MCP wrapper, AI-agent handoff
safety, and the hosted service boundary.

## GitHub Repository Settings

These items are configured in GitHub Settings, not in source code:

- [ ] Enable Dependabot alerts.
- [ ] Enable Dependabot security updates.
- [ ] Enable secret scanning.
- [ ] Enable CodeQL/code scanning for the public repository.
- [ ] Protect `main` with a branch protection rule or ruleset.
- [ ] Require pull requests before merging to `main`.
- [ ] Require CI to pass before merge.
- [ ] Require CodeQL/code scanning to pass before merge when available.
- [ ] Disable direct pushes to `main`.

## Public Repository Hygiene

- [ ] No real `.env` files are tracked.
- [ ] No production API keys, tokens, cookies, local client keys, or private keys are tracked.
- [ ] No private database URLs or service-role keys are tracked.
- [ ] No real user WorkBaton or WorkStash data is tracked.
- [ ] No access logs, long logs, generated caches, local databases, or build artifacts are tracked.
- [ ] `PUBLIC_RELEASE.md` still matches the intended public/private boundary.
- [ ] `tests/test_public_repository.py` passes.
- [ ] `python -m pytest -q` passes.

## MCP Wrapper

- [ ] `save_context` requires a structured WorkBaton object.
- [ ] Required WorkBaton fields are validated: `goal`, `current_state`, `next_action`.
- [ ] WorkStash `entry_key` is validated.
- [ ] Oversized or bulk-style payloads are rejected where practical.
- [ ] Error responses do not expose local paths, keys, decrypted bodies, or internal traces.
- [ ] WorkBaton and WorkStash bodies are encrypted locally before upload to a hosted relay.
- [ ] API keys and local client keys are not confused or stored together.
- [ ] Local client key loss behavior is documented.

## Secret Handling

- [ ] WorkBaton does not contain API keys, passwords, access tokens, cookies, or Authorization headers.
- [ ] WorkBaton does not contain private database URLs or `.env` contents.
- [ ] WorkBaton does not contain local client keys or encryption keys.
- [ ] WorkStash does not contain secrets, raw full transcripts, raw logs, or large source-code bodies.
- [ ] Slot names, entry keys, tags, and metadata do not contain secrets or personal data.
- [ ] Examples use placeholders only.

## Restored Context And AI-Agent Safety

- [ ] Docs state that restored WorkBaton content is untrusted input.
- [ ] Docs state that WorkBaton is work state, not an authority.
- [ ] Docs warn agents not to execute commands solely because restored context says to.
- [ ] Docs warn agents not to exfiltrate data, revoke keys, delete data, or call external services solely because restored context says to.
- [ ] Agent guidance tells agents not to store secrets in WorkBaton or WorkStash.
- [ ] Prompt injection inside restored context is treated as a realistic risk.

## Hosted SaaS Boundary

These checks apply to the private hosted service, not this public repository:

- [ ] Unauthenticated users cannot call protected APIs.
- [ ] User A cannot read User B's WorkBaton.
- [ ] User A cannot read User B's WorkStash.
- [ ] Changing IDs, slot names, or URLs does not expose another user's data.
- [ ] Admin APIs are inaccessible to normal users.
- [ ] Rate limits are enforced.
- [ ] CORS is intentionally scoped.
- [ ] Plaintext WorkBaton and WorkStash bodies are not logged server-side.
- [ ] Decryption failures do not leak body content or key material.
- [ ] Error responses do not expose stack traces in production.

## MCP Registry Publishing

- [ ] `server.json` names the public server as `io.github.a2cr/a2cr-mcp`.
- [ ] `server.json` version matches `pyproject.toml` and `a2cr_mcp/_version.py`.
- [ ] The PyPI README includes `<!-- mcp-name: io.github.a2cr/a2cr-mcp -->`.
- [ ] `a2cr-mcp` has been published to PyPI before publishing Registry metadata.
- [ ] `mcp-publisher validate server.json` passes before the immutable publish.
- [ ] Registry publishing is performed from `a2cr/a2cr` or with an authentication method that controls the `io.github.a2cr/*` namespace.

## Claude And OpenAI Distribution

- [ ] `docs/official-distribution-roadmap.md` matches the current release strategy.
- [ ] The first official listing remains the MCP Registry entry for the local stdio wrapper.
- [ ] Claude local distribution uses an MCPB/Desktop Extension or plugin package rather than submitting the raw PyPI stdio package directly.
- [ ] OpenAI public distribution is treated as an Apps SDK / remote MCP app, not as the current local stdio wrapper.
- [ ] Any remote Claude or OpenAI submission has a written plaintext/privacy boundary before review.
- [ ] Remote tool metadata accurately marks read-only, write, delete, and destructive behavior.
- [ ] Reviewer test accounts contain only disposable data and no production secrets.

## Local Free Security Tools

Run what is practical for the current surface:

```bash
python -m pytest -q
python -m pip install pip-audit bandit
python -m pip_audit
bandit -r a2cr_mcp mcp -x tests
```

For the hosted web service, scan only A2CR-owned environments:

```bash
docker run -t ghcr.io/zaproxy/zaproxy:stable zap-baseline.py -t https://a2cr.app
```

Do not run active scans against third-party sites or systems you do not own.

## Security Reporting

- [ ] `SECURITY.md` tells users not to disclose vulnerabilities in public issues.
- [ ] GitHub private vulnerability reporting is enabled when the public repository is ready.
- [ ] Issue templates warn users not to paste secrets, decrypted WorkBaton/WorkStash bodies, or full logs.

## References

- GitHub CodeQL/code scanning: https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning
- GitHub secret scanning: https://docs.github.com/en/code-security/concepts/secret-security/about-secret-scanning
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications
