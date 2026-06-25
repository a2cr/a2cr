# A2CR Public Release Boundary

This file defines what belongs in the public A2CR release and what must stay
outside it.

The goal is to avoid mixing two different concerns:

- public reference material that helps people use, inspect, and implement A2CR-compatible handoffs
- private hosted SaaS implementation details that belong to A2CR operations

## Repository Roles

| Side | Role | Notes |
|---|---|---|
| `akagi819/a2cr` | private/workbench side | Used for preparation, review, and private development context. |
| `a2cr/a2cr` | public release side | Target public repository for the minimal client, spec, docs, and examples. |

Do not treat the public release branch as a normal feature branch for the
private SaaS repository. It intentionally removes private service surfaces.

## Public Release Scope

The public repository should contain only the material needed to understand,
use, test, and implement the public A2CR client/spec surface.

### Include

- `README.md`
- `LICENSE`
- `NOTICE`
- `SECURITY_CHECKLIST.md`
- `SECURITY.md`
- `TRADEMARK.md`
- `CONTRIBUTING.md`
- `.env.example`
- `server.json`
- `pyproject.toml`
- `a2cr_mcp/`
- `mcp/`
- `docs/concepts.md`
- `docs/mcp-setup.md`
- `docs/claude-desktop-mcpb.md`
- `docs/mcp-registry-publishing.md`
- `docs/official-distribution-roadmap.md`
- `docs/security-model.md`
- `docs/usage.md`
- `docs/spec/`
- `docs/templates/skills/a2cr-agent/`
- `examples/`
- `packages/claude-extension/` for the Claude Desktop MCPB package, excluding
  generated build artifacts and local credentials
- focused tests for the public MCP wrapper and public repository boundary

### Do Not Include

- hosted FastAPI backend implementation
- hosted React dashboard implementation
- Supabase schema, migrations, policies, or production SQL
- billing, admin, operations, or deployment code
- production API keys, local client keys, encryption keys, JWT secrets, cookies, or tokens
- `.env` files or real environment values
- private database URLs or connection strings
- real user WorkBaton or WorkStash data
- access logs, raw logs, generated caches, or build artifacts
- internal runbooks, private product notes, or private business logic

## Layer Model

| Layer | Public? | License / Posture |
|---|---:|---|
| WorkBaton Format specification | yes | Text: CC BY 4.0. Schemas/examples/conformance: Apache-2.0. |
| `a2cr-mcp` official local client | yes | Apache-2.0. |
| Hosted relay service at `a2cr.app` | no | Legacy/private service, not included in this repository. |
| Dashboard, billing, database, operations | no | Proprietary/private. |

The key principle:

```text
The format should be implementable.
The hosted service should not be copied from this repository.
```

## What Others Should Be Able To Do

The public materials should be enough for another developer or company to:

- understand the WorkBaton and WorkStash concepts
- configure the official MCP wrapper
- inspect the security boundary
- validate basic WorkBaton and WorkStash payloads
- build a local WorkBaton-compatible implementation from the public spec

They should not receive enough private implementation detail to clone the hosted
A2CR SaaS business directly from this repository.

## Release Checklist

Before publishing to `a2cr/a2cr`, verify:

- `python -m pytest -q` passes
- `tests/test_public_repository.py` passes
- no private service folders are tracked
- no `.env`, real keys, logs, local databases, or generated caches are tracked
- `README.md` says Apache-2.0 open source and clearly separates legacy/private hosted service surfaces
- `LICENSE`, `NOTICE`, `TRADEMARK.md`, and `docs/spec/LICENSE.md` are present
- `SECURITY.md` and `SECURITY_CHECKLIST.md` are present
- `docs/spec/` contains implementation-level spec files, schemas, examples, and conformance guidance
- `server.json` matches the PyPI package version and README `mcp-name` verification string
- the Claude Desktop MCPB package version and compatibility header match the
  Python wrapper version when released together
- released MCPB artifacts are built with `npm run mcpb:pack`, verified with a
  SHA-256 checksum, and attached to GitHub Release only after explicit
  publication approval
- `docs/official-distribution-roadmap.md` still treats Claude and OpenAI remote submissions as later phases unless the remote privacy boundary is documented
- the branch being pushed contains only intended public-release files
- GitHub Settings are configured for Dependabot alerts, secret scanning, CodeQL/code scanning, branch protection, and pull-request based merges

Useful checks:

```bash
git status --short
git ls-files
python -m pytest -q
```

## Commit Discipline

Keep public release commits separate from private SaaS changes.

When there are unrelated local modifications, stage only the public release
files intentionally. Do not use broad staging commands unless the worktree is
clean and reviewed.

Good:

```bash
git add README.md PUBLIC_RELEASE.md docs/spec tests/test_public_repository.py
```

Risky:

```bash
git add .
```

## 日本語メモ

このファイルは「何を公開してよくて、何を公開しないか」を迷わないための境界線です。

考え方はシンプルです。

- `a2cr/a2cr` は公開用です。
- `akagi819/a2cr` は作業場・非公開情報を含み得る側です。
- 公開するのは、仕様、MCP クライアント、設定例、ドキュメント、検証です。
- 公開しないのは、SaaS 本体、DB、課金、管理画面、運用コード、秘密情報、実ユーザーデータです。

A2CR は「仕様は広げる、ブランドとサービスは守る」という方針です。WorkBaton Format は他の人が実装できるように公開しますが、ホスト型サービス本体を丸ごと公開するわけではありません。

迷ったら、次の基準で判断します。

```text
AI エージェントの引き継ぎ仕様を理解・実装するために必要か？
それとも、A2CR の SaaS 事業そのものを再現するための内部情報か？
```

前者なら公開候補、後者なら非公開です。
