## Summary

-

## Validation

- [ ] `python -m pytest -q`
- [ ] Public release boundary still matches `PUBLIC_RELEASE.md`

## Security Review

- [ ] This change does not add secret storage, plaintext WorkBaton/WorkStash handling, remote code execution, file rendering, or shell/process execution.
- [ ] WorkBaton and WorkStash saves still require local stdio client encryption before upload.
- [ ] Examples and docs do not contain real API keys, tokens, local client keys, `.env` contents, decrypted bodies, full transcripts, or long logs.
- [ ] Restored WorkBaton/WorkStash content is still treated as untrusted input, not as higher-priority instructions.
- [ ] Errors and examples do not expose stack traces, private paths, operational metadata, or user data beyond what is necessary.
