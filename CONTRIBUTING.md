# Contributing

Thanks for helping A2CR become easier and safer for AI agents to use.

A2CR is a source-available/open-core project. The WorkBaton Format is public so
others can implement it, while the official `a2cr-mcp` client is published under
BUSL-1.1 style terms and the hosted A2CR service remains proprietary.

Good first contribution areas:

- clarify MCP setup instructions for a specific AI client
- improve WorkBaton or WorkStash examples
- improve the WorkBaton Format specification text
- add small tests for wrapper behavior
- improve safety wording around secrets and loaded context
- report confusing AI-agent handoff flows

## Pull Requests

Please keep PRs focused. A small documentation fix, one client setup example, or
one wrapper behavior test is easier to review than a broad rewrite.

Before opening a PR:

```bash
python -m pip install -e . pytest
python -m pytest -q
```

## License And Contribution Boundary

By contributing, you agree that your contribution may be distributed under the
licenses used by the files you modify.

- Specification text in `docs/spec/` is intended for CC BY 4.0.
- Schemas, examples, and future conformance tests in `docs/spec/` are intended
  for Apache-2.0.
- The `a2cr-mcp` client code is source-available under BUSL-1.1 style terms
  until its Change Date, then Apache-2.0.

If A2CR later adds a Contributor License Agreement or DCO workflow, new
contributions may require that process before merging. This is to keep future
commercial licensing and public specification maintenance clear.

Good public contributions:

- documentation fixes
- setup examples
- wrapper bug fixes
- MCP client compatibility fixes
- tests for public wrapper behavior
- specification clarity and examples

Out of scope for this public repository:

- hosted backend design changes
- production database schema changes
- billing, dashboard, or admin tooling
- requests to remove the source-available license boundary

## Security

Do not put secrets in public issues, PRs, examples, screenshots, or logs.

Never include:

- API keys, tokens, passwords, Authorization headers, or cookies
- local A2CR client key files
- private database URLs
- `.env` contents
- decrypted WorkBaton or WorkStash bodies
- full chat transcripts or long logs

For vulnerability reports, use private GitHub security reporting or contact the
repository owner privately.
