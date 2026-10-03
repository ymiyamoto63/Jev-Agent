# PoC-1: PreToolUse hook で Agent の model を書き換えられるか

実施日: 2026-10-03 / Claude Code 2.1.288 / メイン会話: Sonnet 5.5（`claude -p` のヘッドレス実行）

## 目的

フィジビリティ検討の R3 を検証する。`PreToolUse` hook の `updatedInput` で Agent ツールの `model` 引数を書き換えたとき、サブエージェントが実際にそのモデルで動くかを確かめる。Jev はまだ使わず、キーワードの固定ルールで代用する（`hooks/route_agent.py`）。

## 構成

- `hooks/route_agent.py`: PreToolUse hook（matcher `Agent|Task`）。`description` と `prompt` をキーワード判定し、`{**tool_input, "model": <選んだモデル>}` を `updatedInput` として返す。判定内容は `$ROUTE_LOG` に JSONL で記録する。
- `run_poc.sh [control|hook|broken]`: 一時ディレクトリに小さなリポジトリを作り、メインエージェントに「Agent を1回だけ呼んで `compute_total` の定義ファイルを探させる」タスクを実行させる。サブエージェントが実際に使ったモデルは、結果 JSON の `modelUsage` で確認する。

## 結果

| # | ケース | Agent 呼び出し時の指定 | hook | 実際のサブエージェントのモデル | 結果 |
|---|---|---|---|---|---|
| 1 | control | `general-purpose`, `model: "opus"` | なし | **Opus 5.5** | 正解 |
| 2 | hook | `general-purpose`, `model: "opus"` | 書き換え（→ haiku） | **Haiku 4.5**（Opus は使われていない） | 正解 |
| 3 | hook / model 指定なし | 組み込みの `Explore`（既定では Opus） | 追加（→ haiku） | **Haiku 4.5** | 正解 |
| 4 | hook / frontmatter で固定 | カスタムエージェント `finder`（frontmatter `model: opus`） | 追加（→ haiku） | **Haiku 4.5** | 正解 |
| 5 | broken（hook が exit 1） | `general-purpose`, `model: "opus"` | 異常終了 | **Opus 5.5**（元の入力のまま実行された） | 正解 |

サブエージェント部分のコスト（各1回、参考値）: Opus $0.149 → Haiku $0.034（#2）。

## わかったこと

1. **`updatedInput.model` の書き換えは有効。** 下げる方向だけでなく、メインエージェントが指定していない場合の追加（#3）、frontmatter の上書き（#4）もできる。サブエージェントのモデルは hook 側で決められる。
2. **`permissionDecision` を付けなくてよい。** `updatedInput` だけで書き換えが反映される。
3. **hook が失敗した場合は元の入力のまま実行される（#5）。** Jev がタイムアウトやエラーのときに処理全体が止まることはない。ただし「元の入力」はメインエージェントが選んだモデル（多くの場合は未指定、つまりメインと同じかエージェントの既定）なので、hook の中で例外を捕まえて**明示的に既定モデルを返す**作りにする。
4. Agent の入力には `description` / `prompt` / `subagent_type` / `model` / `run_in_background` が含まれる。Jev に渡す state は `description` と `prompt` で足りる見込み。
5. hook は Agent の呼び出しごとに1回だけ実行され、メイン会話のモデルは変わらない（Sonnet のまま）。つまりメイン側のキャッシュを壊さない。

## 再現方法

```bash
cd poc1
./run_poc.sh control
./run_poc.sh hook
VARIANT=nomodel ./run_poc.sh hook
VARIANT=frontmatter ./run_poc.sh hook
./run_poc.sh broken
```

1回あたりの API コストは $0.05〜0.2。

## 次（PoC-2）

`route()` を Jev（フィジビリティ検討 §5.2 の質問セット）に置き換える。confidence が低いときに上位モデルへ倒す処理、タイムアウト時に既定モデルへフォールバックする処理を入れ、判定のレイテンシを計測する。
