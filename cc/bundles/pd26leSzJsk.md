# 【Fable5超え】この指示だけを与えておけば、Opus5は世界一のモデルになります【ClaudeCode】 — プレゼント一式
# 2026-08-02 配布 / 3点
# ==========================================================


### 1. Effort早見表＋Opus 5移行チェックリスト（早見表・逆引き）
# 5段階のeffortの使い分けと、Opus 4.8からの移行時に確認すべき項目をまとめた早見表です。

# 🎁 Effort早見表＋Opus 5移行チェックリスト

5段階のeffortの使い分けと、Opus 4.8からの移行時に確認すべき項目をまとめた早見表です。

**受け取り方**: 下のコードブロック右上のコピーボタンでコピーするか、このファイルをそのままダウンロードしてください。

**使い方**: 手元のメモやCLAUDE.md冒頭など、いつでも見返せる場所に貼ってください。

```text
【Opus 5 Effort早見表＋移行チェックリスト】

■ Effortの使い分け（5段階）
□ low — 簡単な作業・サブエージェントへの委任先。積極的に使ってコスト削減
□ medium — 速度とコストのバランス重視。積極的に使ってコスト削減
□ high（既定） — 複雑な推論・難しいコーディング。何も指定しない場合と同じ
□ xhigh — 本格的なエージェント作業・長時間タスクの時だけ明示的に指定
□ max — 最高難度の一発勝負タスクの時だけ
→ YES: まずhighのまま試し、質が落ちなければlow/mediumへ。逆に物足りなければxhigh/maxへ

■ ステップ1：モデルIDの確認
□ コード上のモデルIDが claude-opus-4-8 のままになっていないか
→ YES: claude-opus-5 に更新する

■ ステップ2：thinkingまわりの確認
□ thinking未指定のままmax_tokensを使い回していないか（Opus5はthinkingがデフォルトON。max_tokensは思考＋応答の合計に対する上限）
→ YES: max_tokensを見直す
□ thinking: disabled を effort xhigh/max と併用していないか（400エラーになる）
→ YES: thinkingを有効に戻すか、effortをhigh以下に下げる

■ ステップ3：引き継いだ指示の棚卸し
□ 「検証して」「ダブルチェックして」という旧モデル向けの指示が残っていないか
→ YES: 削除する（Opus5は指示なしで自分の作業を検証するため）
□ Opus4.8時代のeffort設定をそのまま引き継いでいないか
→ YES: 一度evalし直す（公式ドキュメントも「fresh sweepの実施」を推奨）

■ ステップ4：キャッシュへの影響確認
□ 会話の途中でeffortを変更していないか（プロンプトキャッシュが無効になる）
→ YES: 1つの会話内ではeffortを固定し、変えるならワークロード単位にする

指示例: 「このプロジェクトのCLAUDE.mdを、上のチェックリストに沿って棚卸ししてください」
```

**ポイント**: 「まずhighのまま様子を見て、evalで確認できたらlow/mediumに下げる」の順番を守ると失敗しにくい。


### 2. Opus 5 挙動お直し処方箋7選（テンプレート）
# Anthropic公式ドキュメント「Prompting Claude Opus 5」に実際に書かれている指示文ブロックを、症状→処方箋の形でそのまま使える形にまとめました。英語の指示文＋日本語の解説つき。

# 🎁 Opus 5 挙動お直し処方箋7選

Anthropic公式ドキュメント「Prompting Claude Opus 5」に実際に書かれている指示文ブロックを、症状→処方箋の形でそのまま使える形にまとめました。英語の指示文＋日本語の解説つき。

**受け取り方**: 使いたい項目をコピーするか、このファイルごとダウンロードしてください。

**使い方**: 自分のCLAUDE.mdやシステムプロンプトの末尾に、症状が当てはまる項目だけ貼ってください。全部を一度に入れる必要はありません。

---

## 応答・実況まわり

### 1. 応答が長すぎるのを直す

症状: 何も言わなくても応答が長い。effortを下げても短くならない（effortは「考える量」だけを制御し、「話す量」は別）。

```text
Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.
```

長いシステムプロンプトの終盤に置く短縮版:

```text
<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

**ポイント**: この症状はeffortを下げるだけでは直らない。応答の長さは別建てで指示する必要がある。

### 2. 作業中の逐一実況を落ち着かせる

症状: 「これからこれをやります」と逐一実況し、1メッセージの分量も多くなりがち。

```text
Before your first tool call, say in one sentence what you're about to do. While working, give a brief update only when you find something important or change direction. When you finish, lead with the outcome: your first sentence should answer "what happened" or "what did you find," with supporting detail after it for readers who want it.
```

**ポイント**: 実況を止めるのではなく「リズム」を指定するのがコツ。

### 3. 書き出す資料そのものの長さを整える

症状: 会話の応答とは別に、ファイルに書き出すレポート・Markdown文書も長くなりやすい。

```text
Match the length of written documents to what the task needs: cover the substance, but do not pad with filler sections, redundant summaries, or boilerplate.
```

**ポイント**: 会話の簡潔さ指示（1番）とは別に必要な指示。

---

## 検証・範囲まわり

### 4. 頼んでもいない確認・範囲拡大を止める

症状: 指示なしで自分の作業を検証する。旧モデル向けの「必ず検証手順を入れて」「サブエージェントで検証して」が残っていると二重に検証してしまう。頼んだ範囲を勝手に広げることもある。

まず旧モデル向けの検証指示（例:「include a final verification step for any non-trivial task」）は削除してから、次の一言を足す:

```text
Deliver what was asked, at the scope intended. Make routine judgment calls yourself, and check in only when different readings of the request would lead to materially different work. If the request seems mistaken or a better approach exists, say so in a sentence and continue with the task as asked rather than quietly narrowing, widening, or transforming it. Finish the whole task, and stop short of actions that are clearly beyond what was asked.
```

**ポイント**: 「引き算」が先。指示を足す前に、古い検証指示を消す。

### 5. サブエージェントの分身しすぎを止める

症状: 独立していない小さな仕事にまで、他のサブエージェントへの委任を使いたがる。コストと時間が余計にかかる。

```text
Delegate to a subagent only for large tasks that are genuinely independent and parallelizable, such as a wide multi-file investigation. Do not delegate work you can finish yourself in a handful of tool calls, and do not use subagents to verify or double-check your own work. If one subagent can complete the task, use one rather than several, and keep spawn counts low.
```

**ポイント**: Fable 5では逆に「積極的に委任せよ」が公式推奨。モデルをまたいで使い回さないこと。

---

## 自己修正・出力まわり

### 6. 些細な言い直しの逐一報告を止める

症状: 自分の間違いを指示なしでよく直せるが、「さっきの発言を訂正します」と些細な言い直しまで逐一ナレーションしてしまう。

```text
Only correct an earlier statement when the error would change the user's code, conclusions, or decisions. State corrections plainly and briefly, then continue the task. For slips that change nothing for the user, make the fix and move on without noting it.
```

**ポイント**: 自己修正そのものを止める指示ではなく、報告するかどうかの基準を絞る指示。

### 7. thinking無効時の出力漏れを防ぐ（開発者向け・API利用時）

症状: Opus 5はthinkingがデフォルトON。effortがhigh以下でないとthinkingを無効化できない（xhigh/maxとdisabledの併用は400エラー）。無理に無効化すると、ツール呼び出しが文章として漏れたり、内部XMLタグが表示に混ざることがある。

公式推奨はthinkingを有効なままeffortを下げること。どうしても無効化が必要な場合のみ、次の一言を足す:

```text
When you use a tool, you may say a brief sentence first. If no tool can express what the user asked for, say so instead of guessing. Do not include internal or system XML tags in your response.
```

**ポイント**: 「thinking」「タグ」と名指しで禁止するより、この一般化した言い方の方が効くと公式ドキュメントに明記されている。

---

以上、7個です。内訳: 応答・実況まわり3／検証・範囲まわり2／自己修正・出力まわり2。


### 3. Opus 5 vs Fable 5 プロンプト方針 対照表（プロンプト集）
# 同じAnthropicの公式ガイドでも、モデルによって指示の方向が逆になる箇所をまとめた対照表です。

# 🎁 Opus 5 vs Fable 5 プロンプト方針 対照表

同じAnthropicの公式ガイドでも、モデルによって指示の方向が逆になる箇所をまとめた対照表です。

**受け取り方**: 下のコードブロック右上のコピーボタンでコピーするか、このファイルをそのままダウンロードしてください。

**使い方**: 複数モデルを使い分けているプロジェクトのCLAUDE.md・メモに貼ってください。

```text
【Opus 5 vs Fable 5 プロンプト方針 対照表】

■ サブエージェントへの委任
・Fable 5 → 積極的に委任せよ、と明示するのが公式推奨
・Opus 5 → 委任を絞り、上限を決めよ、と明示するのが公式推奨
→ YES: モデルを切り替えるプロジェクトでは、この指示を使い回さない

■ 応答の長さ
・Fable 5 → effortで応答量もある程度連動しやすい
・Opus 5 → effortは「考える量」のみ。「話す量」は別途、簡潔さの指示が必要
→ YES: Opus5移行時は簡潔さの指示を必ず別立てで用意する

■ 価格（入力/出力・per Mtok）
・Fable 5 → $10 / $50
・Opus 5 → $5 / $25（Opus4.8と同額）
→ YES: コスト試算はモデルごとに個別に行う

■ コンテキスト長
・Fable 5 → 1Mトークン（デフォルト兼上限）
・Opus 5 → 1Mトークン（デフォルト兼上限）
→ YES: ここは共通。長文タスクの設計は使い回してよい

指示例: 「今このプロジェクトで使っているモデルはOpus5ですか、Fable5ですか？上の対照表を踏まえて、CLAUDE.mdの指示に矛盾がないか確認してください」
```

**ポイント**: 「同じ会社の公式ガイドだから同じ書き方でいい」と思い込むと、サブエージェント委任の指示が正反対に効いてしまう。
