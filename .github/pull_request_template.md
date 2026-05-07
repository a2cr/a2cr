## Security Review

- [ ] This change does not add file attachment, file rendering, URL fetch, HTML/render preview, shell/process execution, or AI-execution features.
- [ ] If it does add one of those features, the PR includes a dedicated security review, abuse-case regression tests, and a rollback plan.
- [ ] WorkBaton saves still require local stdio client encryption before upload; remote/server-side plaintext save paths remain disabled.
- [ ] Dashboard/admin surfaces still expose metadata only unless the PR explicitly documents and reviews a narrower exception.
