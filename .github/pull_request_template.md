## Summary

-

## Validation

- [ ] `python -m pytest -q`

## Security Review

- [ ] This change does not add secret storage, plaintext WorkBaton/WorkStash handling, remote code execution, file rendering, or shell/process execution.
- [ ] WorkBaton and WorkStash saves still require local stdio client encryption before upload.
- [ ] Examples and docs do not contain real API keys, tokens, local client keys, `.env` contents, decrypted bodies, full transcripts, or long logs.
