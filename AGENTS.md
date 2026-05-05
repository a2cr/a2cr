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
