# Jev × Claude Code モデル自動選択ツール フィジビリティ検討

調査日: 2026-10-03 / 対象: Jev 1.13 (`jev-1.13.0`)、Claude Code（Opus 5.5 / Sonnet 5.5 / Haiku 4.5 / Fable 5.1）

## 1. 結論

**作れる。ただし割り当ての粒度は「サブエージェント単位」にする。メイン会話のモデルを処理ごとに切り替える方式は採用しない。**

| 割り当ての粒度 | 実装 | コスト効果 | 判定 |
|---|---|---|---|
| ① セッション単位（最初のタスク判定でモデルを1つ選ぶ） | 可能（ラッパー CLI） | プラス | **採用** |
| ② サブエージェント単位（フェーズや副作業を Agent に委譲し、委譲ごとにモデルを選ぶ） | 可能（`PreToolUse` hook で Agent の `model` を書き換える） | 大きなプラス | **採用（本命）** |
| ③ メイン会話のツール呼び出しごとにモデルを切り替える | 不可（hook からモデルを変更できない） | 多くの場合マイナス（キャッシュが消える） | **不採用** |

ご懸念のとおり、③はキャッシュヒット率が下がってコストが増えます（§4.1）。ただし「ファイル検索は安いモデルで十分」という狙いそのものは、②の形にすれば実現でき、しかもキャッシュ面でも有利です（§4.2）。

## 2. Jev の仕様（このツールに関係する部分）

出典: [ブログ](https://typesafe.ai/blog/introducing-system-one-models-and-jev)、[docs](https://docs.typesafe.ai/llms.txt)

- **入出力**: `POST https://api.typesafe.ai/v1/systemone` に `state`（テキスト / JSON）と型付きの質問を送る。質問の型は `choice`（選択肢から1つ＋各選択肢の確率）、`score`（序数の段階評価）、`noul`（yes である確率 0〜1）。返り値には `confidence` が付く。テキスト生成はしない。
- **価格**: 入力 $0.042/MTok、出力は無料。2,000 トークンの判定1回で約 $0.00008 なので、コストは無視できる。
- **レイテンシ**: 70〜500ms。
- **制限**: 1リクエスト 64k トークン（state＋最長の質問で 32k）。レート制限は 80 req/s で、現在は変動中。
- **SDK**: Python（`typesafe-sdk`）、JavaScript（`@typesafe-ai/sdk`）、Claude Code 用の公式 skill もあるが、これは Jev を使うコードを書かせるためのもの。
- **公式の位置づけ**: [Jev with coding agents](https://docs.typesafe.ai/introduction/coding-agents) では、Jev はコーディングエージェントの LLM の代わりにはならず、**ルーティングや分類の判定器として組み込むもの**とされている。[Intent routing](https://docs.typesafe.ai/patterns/intent-routing)（リクエストを分類して最適なハンドラや LLM に振り分ける）と [Skill suggestion](https://docs.typesafe.ai/cookbooks/skill_suggestion)（エージェントのターンごとに skill を選ぶ）が公式パターンとして載っており、今回の構想はこの用途にそのまま当てはまる。

### 注意すべき弱点（[jev-1.13 jaggedness](https://docs.typesafe.ai/model-jaggedness/jev-1.13)）

1. **日本語は精度が落ちる**: 主な学習言語は英語で、CJK は動くが精度が低いと明記されている。今回いちばん大きいリスク。
2. **文字どおりに読む・多段の推論に弱い**: 「このタスクの難易度は？」のようなメタ的で間接的な質問は苦手な部類に入る。具体的な質問に分解する必要がある（§5.2）。
3. **state に無関係な情報が多いと精度が落ちる**: 会話履歴やファイル全体をそのまま渡してはいけない。
4. **選択肢の順番に影響される**（先頭の選択肢に寄る）。
5. **プロンプトインジェクションに弱い**: state 内の文章で判定が誘導されうる。

## 3. Claude Code 側で使える仕組み

出典: [model-config](https://code.claude.com/docs/en/model-config)、[sub-agents](https://code.claude.com/docs/en/sub-agents)、[hooks](https://code.claude.com/docs/en/hooks)

| 仕組み | 使えるか | 内容 |
|---|---|---|
| `claude --model X --effort Y` | ○ | 起動時にモデルと effort を指定できる → ①に使う |
| サブエージェントの `model` 指定 | ○ | 優先順は「Agent 呼び出し時の `model` 引数 > frontmatter の `model` > `CLAUDE_CODE_SUBAGENT_MODEL` > メインのモデル」。frontmatter で `effort` も指定できる |
| `PreToolUse` hook の `updatedInput` | ○ | ツール入力を書き換えられる。**Agent ツールの `model` 引数を Jev の判定結果で書き換えれば②になる** |
| hook からメイン会話のモデルや effort を変える | **×** | どの hook の出力にも `model` / `effort` の項目がない。モデルを切り替えられるのはユーザーの `/model` だけ |
| `/model` によるモデル切り替え | △ | キャッシュが消える場合は、Claude Code が警告して確認を求める |
| `opusplan` | ○ | Plan mode は Opus、実行は Sonnet。粒度の粗い既製品で、比較のベースラインに使える |
| 組み込みの Explore エージェント | 注意 | Anthropic API の環境では **Opus** で動く。同名の `Explore` サブエージェントを `model: haiku` で定義すれば上書きできる。Jev がなくても効く手っ取り早い節約策 |

つまり、③は技術的にも hook から実現できません。

## 4. キャッシュ影響の定量評価

`tools/cost_model.py` で試算しました（API 価格、5分 TTL）。

| モデル | 入力 | 出力 | キャッシュ書き込み | キャッシュ読み込み | キャッシュの最小長 |
|---|---|---|---|---|---|
| Fable 5.1 | $10 | $50 | $12.5 | $0.25 | — |
| Opus 5.5 | $4 | $20 | $5.0 | **$0.20** | 512 |
| Sonnet 5.5 | $2 | $10 | $2.5 | **$0.20** | 512 |
| Haiku 4.5 | $1 | $5 | $1.25 | $0.10 | 4096 |

（単位はすべて $/MTok）

キャッシュについて押さえておく点は2つです。

- **プロンプトキャッシュはモデルごとに分かれる。** モデルを切り替えると、それまでの会話全体をキャッシュに書き直すことになる。
- **Opus 5.5 と Sonnet 5.5 はキャッシュ読み込み単価が同じ（$0.20）。** 長い会話では入力コストの大半がキャッシュ読み込みなので、Sonnet に切り替えて減るのは出力と新規入力の分だけになる。

### 4.1 メイン会話のモデルを途中で切り替える（③）

1ターンあたり新規入力 4k、出力 1.5k と仮定。「Opus のまま続ける」と「安いモデルに N ターン切り替えてから Opus に戻す」を比べた結果:

| 切り替え先 | コンテキスト | 1ターン | 3ターン | 10ターン |
|---|---|---|---|---|
| Sonnet | 30k | **+62%** | +32% | +12% |
| Sonnet | 100k | **+164%** | +82% | +29% |
| Sonnet | 300k | **+313%** | +155% | +55% |
| Haiku | 30k | +18% | −4% | −19% |
| Haiku | 100k | +67% | +17% | −15% |

→ **Sonnet への切り替えは、どの条件でも高くつく。** Haiku でも、10ターン以上の長い区間でしか元が取れない。そもそも Haiku はコンテキストが 200k までなので、大きな会話には入りきらない。**③は不採用**とします。

### 4.2 副作業をサブエージェントに出す（②）

ファイル検索や読み込みを Opus のメイン会話で直接やる場合と、サブエージェント（コールドスタート 15k、要約 1.5k を返す）に委譲する場合の比較。委譲後にメイン会話が30ターン続くと仮定しています。

| 委譲先 | 読み込み 3回×2k | 10回×5k | 20回×8k |
|---|---|---|---|
| Haiku | −21% | **−71%** | **−74%** |
| Sonnet | +17% | −48% | −50% |
| Opus（同じモデル） | +84% | −14% | −21% |

→ 委譲すれば、メイン会話に読み込み結果が溜まらず、以降のターンで毎回それを読み直すコストがなくなります。これに安いモデルの単価が加わって効きます。**読み込み量の小さい作業は、委譲せずにメイン会話でやったほうが安い。** ここが判定ポイントの一つです。

### 4.3 Jev 自体のコスト

1回あたり約 $0.0001 で、Claude の1ターン（$0.01〜0.1）より2〜3桁小さく、レイテンシも 0.5 秒以下です。**判定コストはボトルネックになりません。**

## 5. 推奨アーキテクチャ

```
ユーザーのタスク
   │
   ▼
[①入口ルーター] jev-claude CLI
   │  Jev: タスク分類 + 必要能力スコア → (model, effort) を決める
   ▼
claude --model <M> --effort <E>   ← メイン会話は最後までこのモデル（キャッシュを維持）
   │
   │ フェーズや副作業は Agent ツールで委譲（CLAUDE.md / skill で委譲方針を指示）
   ▼
[②PreToolUse hook: matcher=Agent]
   │  Jev: 委譲プロンプトを判定 → updatedInput.model を haiku/sonnet/opus/fable に書き換え
   │  confidence が低ければ「上位寄り」に倒す
   ▼
サブエージェント（1つのモデルで完結するので、内部のキャッシュは保たれる）
   │
   ▼
[③エスカレーション] テストやレビューで失敗したら、1段上のモデルで再実行
```

### 5.1 フェーズとモデルの初期値（Jev で上下に補正する）

| フェーズ | 既定モデル | Jev で見る観点 |
|---|---|---|
| 要件定義 | Opus | 曖昧さ、利害関係の多さ → Fable に上げる / 定型的なら Sonnet に下げる |
| 設計 | Opus | 影響範囲（複数モジュールか）、新規アーキテクチャか |
| 実装 | Sonnet | 変更が局所的か、並行処理・セキュリティ・アルゴリズムを含むか → Opus に上げる |
| テスト作成・実行 | Sonnet / Haiku | 実行してログを読むだけなら Haiku |
| コードレビュー | Opus | diff の規模、セキュリティ観点の有無 |
| 検索・調査・ログ読み | Haiku | 判断を含まない読み込み作業か |

### 5.2 Jev への質問設計（「難易度は？」と1問で聞かない）

弱点（文字どおりに読む、多段推論に弱い）を避けるため、具体的な質問に分解し、重み付けと合算はコード側で行う（[Composite scoring](https://docs.typesafe.ai/patterns/composite-scoring) パターン）。

```python
questions = {
  "kind": Choice(instructions="Which kind of work does the task request?",
                 criteria={"search": "Find or read files, logs, docs; no edits",
                           "mechanical_edit": "Rename, format, small local fix",
                           "feature": "Implement new behavior",
                           "design": "Decide architecture or requirements",
                           "review": "Judge correctness of existing changes"}),
  "multi_module": Noul(instructions="The task requires changing more than one module or component."),
  "ambiguous":    Noul(instructions="The task leaves important requirements unstated."),
  "risky_domain": Noul(instructions="The task involves security, concurrency, data migration, or money."),
  "novelty":      Score(instructions="How much original reasoning the task needs",
                        criteria=["Follows an obvious existing pattern",
                                  "Needs some judgment", "Needs new design or deep debugging"]),
}
# モデル = f(kind, Σ w_i * p_i)。confidence < しきい値なら1段上のモデルにする
```

- **日本語対策**: ②の委譲プロンプトは、CLAUDE.md で「Agent への指示は英語で書く」と指定すれば英語にできるので、Jev に英語で渡せる。①の入口でユーザーの日本語をそのまま渡す箇所は、精度を実測し、低ければ confidence で判定を保守的にする。
- **state を最小にする**: 委譲プロンプトだけを渡し、会話履歴は渡さない。

## 6. リスクと未検証事項

| # | リスク / 未検証事項 | 影響 | 対策・検証方法 |
|---|---|---|---|
| R1 | Jev が「必要なモデル」を正しく判定できるか | 安すぎるモデルを選ぶと、やり直しで逆に高くつく | **評価セットが必要**。同じタスクを各モデルで実行し「成功した中で最も安いモデル」を正解ラベルにして、Jev ルーターの正解率と「完了タスクあたりのコスト」を測る |
| R2 | 日本語の精度 | 判定がぶれる | 英語の委譲プロンプトと日本語入力で精度を比べる |
| R3 | `PreToolUse` の `updatedInput` で Agent の `model` を書き換えられるか | ②の前提 | **検証済み（PoC-1）**。明示指定の上書き・未指定時の追加・frontmatter の上書きのいずれも有効。hook が失敗した場合は元の入力のまま実行される（`poc1/README.md`） |
| R4 | 委譲によるコンテキストの欠落 | サブエージェントの品質が下がる | 委譲プロンプトのテンプレートを決める。fork（キャッシュを共有するがモデルはメインと同じ）との使い分け |
| R5 | TypeSafe は early access。レート制限も変動中 | 可用性 | Jev がタイムアウトやエラーのときは既定のモデルにフォールバックする |
| R6 | プロンプトやコードの一部を第三者（TypeSafe）に送る | 機密性 | 学習には使わないと明記されているが、ZDR は enterprise のみ。送るのは委譲プロンプトだけにする |
| R7 | 比較対象（ベースライン） | 効果の誤認 | 「Opus 5.5 のみで effort を下げる」「`opusplan`」「Explore を Haiku に固定するだけ」と比較する。Jev なしの単純な策でも効果の多くが取れる可能性がある |
| R8 | サブスクリプション（Pro/Max）利用時 | 「コスト」は利用枠になる | 利用枠もモデルで重み付けされるので、方針は同じ |

## 7. 次のステップ（PoC 計画）

1. **PoC-1（1日）**: `PreToolUse(Agent)` hook で `model` を書き換えられることを確認する（R3）。最初は Jev なしの固定ルールで試す。
2. **PoC-2（実装済み・モックで検証済み、実際の Jev は未検証）**: `jevroute/`、`poc2/README.md`。 Jev のルーター（§5.2 の質問セット）と hook をつなぎ、confidence が低いときに上位モデルへ倒す処理とフォールバックを入れる。
3. **評価（1週間）**: 典型タスク20〜50件について、全モデルで成否とコストを記録して正解ラベルを作る。ルーター、各ベースライン（R7）、Opus のみ、で「完了タスクあたりのコスト」と成功率を比べる。
4. 結果がよければ、入口の CLI（①）、エスカレーション（③）、Claude Code plugin（skill＋hook＋agents 一式）として配布形態に仕上げる。

### 想定する配布形態

**Claude Code plugin** にまとめる:

- `hooks/route_agent.py`（PreToolUse, matcher `Agent`）: Jev を呼んで `model` を書き換える
- `agents/*.md`: フェーズ別のサブエージェント（requirements / design / implement / test / review / explore）
- `skills/jev-route/SKILL.md`: 委譲方針（いつ委譲するか、プロンプトは英語、要約で返す）
- `bin/jev-claude`: 入口ルーター（①）

## 8. PoC-3 第1回の結果（2026-10-03、`eval/README.md`）

- 20タスク × 3モデルの結果: Haiku 19/20、Sonnet 20/20、Opus 20/20。費用は $0.84 / $1.48 / $3.23。
- 小さなコードベースで仕様が明確な委譲タスクでは、作業の種類にかかわらず Haiku で足りた。
- 「Haiku で始め、失敗したら上位で再実行」（20/20、$0.91）が oracle（$0.89）とほぼ同じ結果だった。現在の判定ロジック（mock）は保守的すぎて、費用は oracle の約2倍。
- **方針の修正案**: 自動で検証できるタスクは、安いモデルから始めて失敗時に上位で再実行するのを基本にする。Jev の判定は、検証できないタスクのモデル選択と、最初から上位モデルに回すべき難しいタスクの見極めに使う。難しいタスク群での評価（第2回）で、この案が正しいか確かめる。
