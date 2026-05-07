# WorkBaton Zero-Knowledge Encryption Design

Updated: 2026-05-06

この文書は、A2CR WorkBaton をゼロ知識化するための設計メモである。対象は WorkBaton の保存・読込・再開に限定し、WorkThreads は共有鍵管理が別問題になるため本設計の対象外とする。

## Repository Handling

この設計書および関連する計画書は作業用文書である。ユーザーが公開を明示的に依頼しない限り、commit や push は不要である。

## 1. 前提

- A2CR は AI ではなく、AI 同士が作業を受け渡すための WorkBaton / WorkThreads レイヤーである。
- 現状の WorkBaton は Fernet によるアプリケーション層暗号化を使っている。
- 現状はサーバーが `FERNET_KEY` を持ち、保存時に本文を暗号化し、読込時に本文を復号して MCP/API へ返す。
- そのため、DB を直接見ただけでは本文を読みにくいが、サーバー runtime は復号可能であり、ゼロ知識とは言えない。
- ゼロ知識と呼ぶには、A2CR サーバーへ平文本文と復号鍵を渡さない必要がある。

## 2. 成功条件

- WorkBaton 本文の平文は、A2CR API、MCP server、DB、dashboard、運用ログに渡らない。
- A2CR サーバーは WorkBaton 本文を復号できない。
- Dashboard は従来どおり metadata のみを表示する。
- `slot_name`、`slot_number`、期限、サイズ、token 概算、load count などの metadata はサーバーに残る。
- 既存の非ゼロ知識 Slot は明示的に区別され、黙ってゼロ知識扱いしない。
- WorkThreads の暗号方式は別設計に残す。

## 3. 非目標

- WorkThreads message 本文のゼロ知識化。
- 複数ユーザー間の共有鍵、招待、鍵ローテーション。
- サーバー側での本文検索、本文要約、本文検査。
- KMS/HSM や DB 透過暗号化だけでゼロ知識と表現すること。

## 4. 信頼境界

### サーバーが知ってよい情報

- `user_id`
- `slot_name`
- `slot_number`
- `expires_at`
- `size_bytes`
- `compressed_tokens`
- `detail_level`
- `model_source`
- `load_count`
- access log metadata
- 暗号文、nonce、暗号方式 version、KDF metadata

### サーバーが知ってはいけない情報

- WorkBaton 本文の平文 JSON。
- 本文復号鍵。
- 復号鍵を導出できる passphrase。
- Authorization header、API key、DB URL、OAuth secret などの secret。

## 5. 暗号方式

推奨する初期方式は、MCP client 側での envelope encryption である。

1. AI client または A2CR MCP wrapper が WorkBaton JSON を作る。
2. client 側でランダムな content encryption key を生成する。
3. WorkBaton JSON を AEAD で暗号化する。
4. content encryption key は user secret から導出した key encryption key で包むか、client local key store で保持する。
5. A2CR サーバーへは暗号文と暗号 metadata だけを送る。
6. 読込時、A2CR サーバーは暗号文を返すだけにする。
7. client 側で復号し、AI に平文 WorkBaton を渡す。

初期実装では、広い互換性と実装容易性を優先し、次のどちらかを選ぶ。

| 選択肢 | 内容 | 長所 | 注意点 |
|---|---|---|---|
| A | user passphrase から Argon2id または PBKDF2 で鍵導出 | 端末をまたいで再開しやすい | passphrase 入力 UX と紛失時の復旧不可を説明する必要がある |
| B | MCP wrapper がローカル key file を生成して保持 | UX が軽い | 別端末・別AI clientへの移行には key file の移動が必要 |

MVP では B を先に実装し、公開説明では「この端末/このMCP設定で復号可能」と明示するのが最小変更である。端末をまたぐ Pro 体験は A または専用 recovery flow を後続設計にする。

## 6. API 変更方針

既存 API を壊さないため、平文保存 API をすぐ削除せず、暗号化済み payload 用の field を追加する。

### 保存

新しい request では `content` の代わりに `encrypted_content` を受ける。

```json
{
  "slot_name": "example",
  "slot_number": 1,
  "encrypted_content": {
    "version": 1,
    "alg": "XChaCha20-Poly1305",
    "nonce": "...",
    "ciphertext": "...",
    "key_wrap": {
      "type": "local-key",
      "kid": "..."
    }
  },
  "size_bytes": 1234,
  "compressed_tokens": 456,
  "model_source": "codex"
}
```

`content` が送られた場合は従来モードとして保存する。`encrypted_content` が送られた場合、サーバーは本文 schema validation を行わず、暗号 metadata の形式とサイズだけを検証する。

### 読込

ゼロ知識 Slot の読込 response は暗号文を返す。

```json
{
  "slot_name": "example",
  "slot_number": 1,
  "encryption_mode": "client",
  "encrypted_content": {
    "version": 1,
    "alg": "XChaCha20-Poly1305",
    "nonce": "...",
    "ciphertext": "...",
    "key_wrap": {
      "type": "local-key",
      "kid": "..."
    }
  },
  "expires_at": "...",
  "compressed_tokens": 456,
  "model_source": "codex",
  "load_count": 1
}
```

MCP wrapper はこの response を受け取った後、client 側で復号して、既存の `LoadResponse.content` と同等の形に整える。

## 7. DB 変更方針

`contexts.content` は暗号文格納先として継続利用できるが、モード識別のために列を追加する。

- `encryption_mode text NOT NULL DEFAULT 'server'`
- `encryption_version integer NOT NULL DEFAULT 1`
- `encryption_metadata jsonb`

既存の `encryption_key_version` は server-side Fernet 用のまま残す。client-side mode では復号鍵 version ではなく payload version を見る。

## 8. 既存 Slot の移行

既存 Slot は `encryption_mode = 'server'` として扱う。

- 自動でゼロ知識へ変換しない。
- ユーザーまたは AI client が一度 `load_context` で読み、client 側で再暗号化して `save_context` し直した場合のみ `client` mode になる。
- UI では `Server-encrypted` と `Client-encrypted` を区別する。
- 公開説明では、server-encrypted は「通常管理画面やDB直接閲覧からは保護するが、ゼロ知識ではない」と書く。

## 9. 実装タスク分解

1. DB migration を追加する。
   - verify: migration 適用後、既存 tests が contexts table を作成できる。
2. schema に `encrypted_content` と `encryption_mode` を追加する。
   - verify: 平文 request と暗号文 request の validation test を追加する。
3. Web Context service で client-side encrypted payload をそのまま保存・読込する。
   - verify: server が復号処理を呼ばない unit test を追加する。
4. MCP wrapper に client-side encrypt/decrypt helper を追加する。
   - verify: save -> load roundtrip で server 側は暗号文のみ保持し、MCP tool response は従来どおり平文 content を返す。
5. Dashboard metadata に encryption mode を表示する。
   - verify: dashboard API が本文を返さない既存 test を維持し、mode だけ返る test を追加する。
6. SECURITY / README の表現を更新する。
   - verify: 「zero-knowledge」と「server-encrypted」の違いが明示されている。

## 10. 表現ルール

- client-side mode が入るまでは、A2CR 全体をゼロ知識とは呼ばない。
- server-side Fernet mode は「application-layer encrypted」「not zero-knowledge」と呼ぶ。
- client-side mode だけを「zero-knowledge WorkBaton」または「client-encrypted WorkBaton」と呼ぶ。
- WorkThreads にはこの表現を流用しない。

## 11. 未決事項

- MVP の鍵保管を local key file にするか、passphrase 方式にするか。
- browser dashboard からゼロ知識 Slot を作る場合、WebCrypto を使うか、MCP 経由に限定するか。
- key loss 時の UX。ゼロ知識ではサーバーが復旧できないため、削除または上書きしかできない。
- `compressed_tokens` を client 計算にする場合、client ごとの差を許容するか。
