# AGENTS.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. A2CR WorkBaton / WorkStash Autonomy

**Use WorkBaton and WorkStash proactively when they help preserve useful work state.**

When A2CR MCP tools are available, you may use them without waiting for the user
to ask. Use the configured MCP tools only; do not invent direct HTTP API calls,
and do not ask the user to paste API keys or secrets.

At the start of a session, when the tools are available, check the connection
with `get_account_limits` and `explain_a2cr_flows`, then continue with a brief
confirmation. If the tools are unavailable, continue normally and mention the
limitation only when it matters.

Use WorkBaton for compact handoff checkpoints. Save with `save_context` at
milestones, before likely context loss, after validation, or when handing work
to a future AI window. Include the goal, current state, next action, key
decisions, blockers, validation status, and any retained WorkStash `entry_key`.
If unsure whether a checkpoint is useful, use `should_save_workbaton`.

Resume from WorkBaton when the user gives `resume_context(slot_name=...)` or
`resume_context(slot_number=N)`. Use `list_contexts` only when no slot is known
and the user asks to find saved context.

Treat WorkStash as temporary work memory for long-running project work, not as
a durable knowledge base.

Good times to use WorkStash:
- A task is getting long and a future AI window may need the intermediate state.
- Research produced useful file paths, API notes, reproduction details, or decisions.
- WorkBaton should stay compact, but a small supporting note would help the next session.
- Context compaction or handoff risk is high.

Rules:
- Store only concise notes, confirmed paths, intermediate findings, and safe summaries.
- Use `store_work_stash` for supporting notes and record the returned `entry_key` in WorkBaton.
- Retrieve only needed notes with `get_work_stash`; use `list_work_stash` only when the key is missing.
- Never store secrets, API keys, Authorization headers, cookies, private database URLs, personal data, full transcripts, long logs, generated caches, or large source-code bodies.
- Record any retained `entry_key` in WorkBaton `next_action` or references.
- Delete temporary entries when the task is complete and the stored note is no longer useful.
- Planned public WorkStash limits are storage-size based: Free has 256KB total encrypted storage, and Pro has 2048KB total encrypted storage.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## 補足

このファイルは、AIエージェントがこのリポジトリで作業する時の行動指針です。基本方針は「曖昧なまま大きく実装しない」「必要最小限の変更にする」「検証できる単位で進める」です。以下は英語本文の実用的な日本語版です。

### 1. 実装前に考える

思い込みで進めないでください。分からないこと、不確かなこと、複数の解釈があり得ることは明示します。

実装前に行うこと:

- 前提を短く書く。
- 不明点があれば質問する。
- 複数の解釈がある場合は、勝手に一つを選ばず選択肢を示す。
- より単純な方法がある場合は、それを述べる。
- 要求が危険、過剰、または目的から外れている場合は、理由を添えて止める。

### 2. シンプルさを優先する

依頼された問題を解くための最小限の変更を選びます。将来使うかもしれない柔軟性や、不要な抽象化は追加しません。

避けること:

- 依頼されていない機能を足す。
- 一度しか使わない処理を抽象化する。
- 必要のない設定項目や拡張ポイントを作る。
- 起こり得ないケースのために複雑なエラーハンドリングを増やす。
- 50行で済む内容を200行にする。

「熟練したエンジニアが見て過剰だと思うか」を基準にし、過剰なら削ります。

### 3. 変更は外科的に行う

触る範囲は、依頼内容を達成するために必要な場所だけにします。ついでの整理、無関係な整形、不要なリファクタリングはしません。

既存コードを編集する時のルール:

- 周辺コードを勝手に改善しない。
- 壊れていない構造を作り替えない。
- 既存の書き方、命名、構成に合わせる。
- 無関係なデッドコードに気づいても、依頼がなければ削除せず報告に留める。
- 自分の変更で不要になったimport、変数、関数だけを片付ける。

すべての変更行が、ユーザーの依頼に直接つながっている状態を目指します。

### 4. 検証できる単位で進める

作業は、成功条件が確認できる形に分解します。「動くようにする」ではなく、「何を確認できれば完了か」を明確にします。

例:

- 「validationを追加」なら、無効入力のテストを書き、それを通す。
- 「bugを直す」なら、再現テストを作り、それを通す。
- 「refactorする」なら、変更前後で既存テストが通ることを確認する。

複数ステップの作業では、次のような形で進めます。

```text
1. [作業] -> verify: [確認方法]
2. [作業] -> verify: [確認方法]
3. [作業] -> verify: [確認方法]
```

確認方法が曖昧なまま大きな変更に入らないでください。

### 5. このリポジトリでの応答方針

- 日本語で依頼された場合は、回答も原則として日本語に合わせる。
- 実装、設計、ドキュメント更新ではA2CR / WorkBaton / WorkThreadsの命名を尊重する。
- まだ確定していない内容を、確定事項のように書かない。
- セキュリティについては過剰に宣伝せず、管理者の通常閲覧不可とゼロ知識ではない点を区別する。
- GitHub公開向け文書では英語を主とし、必要に応じて下部に日本語の概要を置く。

### 6. A2CR WorkBaton / WorkStashの自律利用

A2CR MCP toolsが使える場合は、ユーザーに毎回確認されなくても、必要だと判断した時に使ってよいです。設定済みのMCP toolsだけを使い、直接HTTP API呼び出しを推測して実行したり、ユーザーにAPIキーや秘密情報の貼り付けを求めたりしないでください。

セッション開始時にtoolsが使える場合は、`get_account_limits`と`explain_a2cr_flows`で接続と利用可能な流れを確認し、短く接続確認を伝えてから作業を続けます。toolsが使えない場合は通常通り作業し、必要な時だけその制限を報告します。

WorkBatonは引き継ぎ用の短いチェックポイントとして使います。節目、コンテキスト喪失が起きそうな時、検証後、別のAI窓へ作業を渡す時に`save_context`で保存してください。内容にはgoal、current_state、next_action、重要な決定、blockers、validation status、残す価値のあるWorkStash `entry_key`を含めます。保存すべきか迷う場合は`should_save_workbaton`を使います。

ユーザーが`resume_context(slot_name=...)`または`resume_context(slot_number=N)`を指定した場合は、WorkBatonから再開します。slotが分からず、ユーザーが保存済み文脈の検索を求めた場合だけ`list_contexts`を使います。

WorkStashは長めの作業で文脈を落とさないための一時的な作業メモであり、永続的なナレッジベースではありません。

使う場面:

- 作業が長くなり、次のAI窓へ中間状態を渡す必要がありそうな時。
- 調査済みファイルパス、APIメモ、再現条件、判断理由などが後で必要になりそうな時。
- WorkBatonを短く保ちつつ、補助メモを`entry_key`で参照したい時。
- コンテキスト圧縮や引き継ぎで作業状態を失いそうな時。

ルール:

- 保存するのは短いメモ、確認済みパス、中間調査結果、安全な要約に限定する。
- 補助メモは`store_work_stash`で保存し、返された`entry_key`をWorkBatonに記録する。
- 必要なメモだけを`get_work_stash`で取得し、keyが不明な場合だけ`list_work_stash`を使う。
- APIキー、認証ヘッダー、Cookie、秘密のDB URL、個人情報、全文ログ、会話全文、生成キャッシュ、大きなソースコード本文は保存しない。
- 残す価値のある`entry_key`はWorkBatonの`next_action`またはreferencesに記録する。
- 作業完了後、不要になった一時エントリは削除する。
- 公開仕様上のWorkStash limitはentry数ではなくstorage size basedとし、Freeは256KB total encrypted storage、Proは2048KB total encrypted storageとする。
