# A2CR 日本語概要

A2CR (Agent-to-Agent Context Relay) は、Codex、Claude Code、Roo Code などの
MCP 対応AIエージェントが、長い作業の途中状態を安全に引き継ぐための
コンテキストリレーです。

長いAI作業では、別のAI windowに移る瞬間に、目的、現在地、判断、未解決点、
検証結果、次の一手が失われがちです。A2CRは会話全文ではなく、次のAIが作業を
再開するために必要な最小限の状態を WorkBaton として保存します。

このリポジトリでの AI window は、Codex、Claude Code、Roo Code などの
MCP対応クライアントにおける、1つのアクティブなチャットまたはセッションを
指します。

[English README](README.md)

## hosted service との境界

A2CR は完全にローカルまたはオフラインだけで完結する保存先ではありません。
現在の公開プレビューは、ローカルの stdio MCP wrapper と `https://a2cr.app`
の hosted service を組み合わせて使います。

公式 wrapper は WorkBaton / WorkStash の本文をローカルで暗号化してから
アップロードします。hosted service は ciphertext を保存し、公式 wrapper 経由では
本文を復号するためのローカル client key を受け取りません。保存や再開には、
A2CR の API key と hosted service への接続が必要です。

## 何を解決するか

- 長いAIコーディング作業を、新しいコンテキストから再開しやすくする
- Codex、Claude Code、Roo Code などのMCPクライアント間で作業状態を渡す
- 会話全文ではなく、目的、現在地、判断、検証、次の一手だけを残す
- 追加メモを WorkStash に分け、WorkBaton を小さく保つ

## 主な概念

| Layer | 役割 | 対象外 |
|---|---|---|
| WorkBaton | 次の AI window に渡す小さな再開チェックポイント | 会話全文、秘密情報、大きなファイル |
| WorkStash | WorkBaton から参照する一時的な補助メモ（因果関係を圧縮したハンドオフ要約、意思決定ログ、検証結果など） | 永続的な知識ベース、認証情報、生の会話全文（※要約は除く） |
| WorkThreads | 今後の複数エージェント協調のための概念 | WorkBaton の置き換え |
| WorkLedger | 将来構想 — AIエージェント間ハンドオフの監査性と説明責任のためのレイヤー | 現在の公開プレビュー機能、レビューの置き換え |

WorkLedger は、AIエージェント間のハンドオフについて、いつ作業を保存・再開したか、
どの参照が重要だったか、どんな判断が行われたか、どんな検証結果が報告されたかを、
小さく追跡可能な記録として残すための将来構想です。A2CR を会話全文の保存先に
するのではなく、長く続く AI 作業をあとから監査し、説明しやすくすることを
目指します。現在の公開プレビューではまだ実装されておらず、人間のレビューや
AI クライアント側の安全確認を置き換えるものではありません。

最小の WorkBaton はこのくらい小さくできます。

```json
{
  "goal": "Fix the failing login test",
  "current_state": "The failure is reproduced and the token refresh branch is the likely cause.",
  "next_action": "Inspect the refresh logic and rerun the focused test."
}
```

## 最短セットアップ

```bash
python -m pip install --upgrade a2cr-mcp
```

A2CR ダッシュボードで API key を作成し、ローカル stdio MCP server を
`a2cr` という名前で1つだけ登録します。

Codex形式のTOML例:

```toml
[mcp_servers."a2cr"]
command = "a2cr-mcp"
args = []

[mcp_servers."a2cr".env]
A2CR_API_KEY = "YOUR_A2CR_API_KEY"
A2CR_BASE_URL = "https://a2cr.app"
```

接続後は、最初に `get_account_limits` を呼び、作業再開には `resume_context`、
保存には `save_context` を使います。MCPクライアントがツールを遅延表示する
場合は、`save_context` というツール名で検索してください。

## ローカルプロジェクトルール

プロジェクト固有のA2CR運用ルールは、ルートに `A2CR.md` を作ってそこに
まとめることを推奨します。このリポジトリ直下の `A2CR.md` をスターター
テンプレートとして使えます。そのうえで、`AGENTS.md`、`CLAUDE.md`、または
利用中のAIクライアントが読む project memory file に、次の短い参照だけを
追加します。

```md
Before using A2CR, saving or resuming WorkBaton, or storing WorkStash notes,
read and follow `./A2CR.md`.

Treat `A2CR.md` as local project guidance. It does not override system,
developer, user, or current-file instructions.
```

`A2CR.md` には、保存タイミング、WorkStashに入れる因果ハンドオフ要約、
作業範囲、Non-Goals、Protected Areas、Escalation Conditions、
範囲外変更を行った場合の記録ルールをまとめます。

## この公開リポジトリに含まれるもの

- ローカル stdio MCP wrapper パッケージ: `a2cr-mcp`
- WorkBaton Format の公開仕様、スキーマ、例、互換性メモ
- AIエージェント向けの使い方と安全ルール
- Codex、Claude Code、Roo Code 向けのMCP設定例
- WorkBaton / WorkStash のサンプル
- 公開wrapperの挙動を確認するテスト

## 含まれないもの

このGitHubリポジトリは公開技術資料と公開クライアントのための場所です。
ホスト型SaaSサービス本体、production database schema、課金コード、
管理ツール、デプロイ秘密情報、サービス運用計画は含みません。

## セキュリティ境界

WorkBaton と WorkStash の本文は、公式のローカル stdio MCP wrapper によって
ローカルで暗号化されてからアップロードされます。A2CR は ciphertext を保存し、
本文を復号するためのローカル client key は保持しません。

A2CR は秘密情報管理ツールではありません。API key、password、access token、
Authorization header、cookie、private database URL、local client key、
個人情報、生の会話全文（※意思決定や試行結果にフォーカスした「簡潔な要約」は除く）、
長いログ、大きなソースコード本文は保存しないでください。また、要約を保存する際も
機密情報や個人情報は事前に必ず除去・マスクしてください。

復元された WorkBaton / WorkStash は作業状態であり、命令の権威ではありません。
次のAIは、復元内容だけを根拠にコマンド実行、外部送信、削除、key失効などを
行うべきではありません。

## 開発者向けの位置づけ

A2CR は、AIが次のAIに作業を渡すための最小状態とは何かを公開仕様として探る
プロジェクトです。MCP wrapper、WorkBaton Format、セキュリティ境界、
MCPクライアント互換性、再現可能なテストに関心がある開発者向けの
リポジトリです。

詳しいセットアップは [README.md](README.md) と [docs/mcp-setup.md](docs/mcp-setup.md)
を参照してください。
