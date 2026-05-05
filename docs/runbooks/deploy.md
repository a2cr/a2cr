# A2CR Deploy Runbook

This runbook describes the MVP deployment path: one Railway service serves the React/Vite SPA, FastAPI APIs, and Streamable HTTP MCP at the same public origin.

## Production Shape

- Runtime: Railway Dockerfile service
- Database/Auth: Supabase Postgres and Supabase Auth
- Public origin: one Cloudflare-managed domain pointing to Railway
- API health: `/api/v1/health`
- Web UI: `/login`, `/dashboard`, `/settings`, `/pricing`
- MCP endpoint: `/mcp`
- Cleanup job: protected Railway job using `python -m services.maintenance expire-contexts`

## Railway Variables

Required runtime variables:

```text
APP_ENV=production
DATABASE_URL=postgresql+psycopg://a2cr_app:<password>@<host>:5432/<db>
FERNET_KEY=<Fernet.generate_key() output>
API_KEY_HASH_SECRET=<32+ random chars>
AUDIT_HASH_SECRET=<32+ random chars>
A2CR_SERVICE_URL=https://<public-domain>/mcp
A2CR_PUBLIC_ORIGIN=https://<public-domain>
A2CR_API_KEY_PREFIX=sk-a2cr
SUPABASE_JWT_SECRET=<Supabase JWT secret>
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=https://<project-ref>.supabase.co/auth/v1
```

Required browser build variables:

```text
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<public anon key>
VITE_A2CR_SERVICE_URL=https://<public-domain>/mcp
VITE_A2CR_API_BASE=
```

For Dockerfile build args, pass the public anon key as `PUBLIC_SUPABASE_ANON`; the Dockerfile maps it to `VITE_SUPABASE_ANON_KEY` only during `npm run build`.

Do not set `SUPABASE_SERVICE_ROLE_KEY` on the Railway runtime service. Startup rejects it.

## Build And Deploy

1. Confirm `main` is green locally:

```bash
python -m pytest -q
cd web
npm ci
npm run build
```

2. Create a Railway service from the GitHub repository.

3. Confirm Railway uses `Dockerfile` and `railway.json`.

4. Add the variables above.

5. Deploy. The Dockerfile builds React first, installs Python dependencies, copies `web/dist`, then starts:

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Smoke Checks

Run after every deploy:

```bash
curl -fsS https://<public-domain>/api/v1/health
curl -fsS https://<public-domain>/dashboard | head
```

Expected:

- health returns `{"status":"ok"}`
- `/dashboard` returns the SPA shell
- `/api/missing` returns 404
- direct reload of `/login`, `/settings`, and `/pricing` returns the SPA shell
- requests with an unexpected `Origin` are rejected with 403

## Cleanup Job

Create a protected Railway job using the same image and variables:

```bash
python -m services.maintenance expire-contexts
```

Recommended initial schedule: every 10 minutes.

The job only calls `SELECT app.expire_contexts()`. The database function logs `context.expire` with sanitized metadata and deletes only expired rows. It does not decrypt context bodies.

## Rollback

1. Roll back the Railway deployment to the previous successful image.
2. Do not roll back database migrations unless a specific migration is proven faulty.
3. If a secret may be exposed, revoke/rotate it before redeploying.
4. Confirm `/api/v1/health`, `/dashboard`, and `/mcp` after rollback.

---

## 概要

A2CRのMVP本番配置は、Railwayの1サービスでReact/Vite SPA、FastAPI API、Streamable HTTP MCP `/mcp` を同一origin配信する構成です。

## 本番構成

- Runtime: Railway Dockerfile service
- DB/Auth: Supabase Postgres と Supabase Auth
- Public origin: Cloudflare管理ドメインからRailwayへ接続
- API health: `/api/v1/health`
- Web UI: `/login`、`/dashboard`、`/settings`、`/pricing`
- MCP endpoint: `/mcp`
- Cleanup job: `python -m services.maintenance expire-contexts`

## Railway環境変数

通常runtimeには `SUPABASE_SERVICE_ROLE_KEY` を絶対に置きません。置かれている場合、起動時に拒否します。

`FERNET_KEY`、`API_KEY_HASH_SECRET`、`AUDIT_HASH_SECRET` は本番ごとに生成した値を使います。`A2CR_SERVICE_URL` は `https://<public-domain>/mcp` のような公開HTTPS URLにします。

## デプロイ後確認

- `/api/v1/health` が `{"status":"ok"}` を返す
- `/dashboard` 直アクセスでSPAが返る
- `/mcp` が同一originで到達できる
- 想定外OriginからのCORS/preflightが403になる
- `SUPABASE_SERVICE_ROLE_KEY` なしで起動している

## Cleanup job

期限切れ削除はアプリが本文を復号して処理するのではなく、DB関数 `app.expire_contexts()` だけを呼びます。削除前に `context.expire` のsanitized logを残し、期限切れではないrowは削除しません。
