# PoC-2: Jev ルーター（差し替え可能なバックエンド）

実施日: 2026-10-03 / Claude Code 2.1.288 / TypeSafe API キーなし

## 目的

PoC-1 の固定ルールを、Jev の判定に置き換える。**API キーが用意できるまでは、モック（Jev ではない）で全体の流れを先に検証**しておき、キーが入ったら環境変数1つで本物の Jev に切り替えられる形にする。

## 構成（`jevroute/`、Python 標準ライブラリのみ）

| ファイル | 役割 |
|---|---|
| `questions.py` | Jev に送るリクエスト。state は委譲された作業だけ（`agent_type` / `summary` / `task`、6,000 文字で打ち切り）。質問は1問1判断で、`kind`（choice、7種類）、`edits_code` / `multi_module` / `ambiguous` / `risky_domain`（noul）、`novelty`（score、3段階） |
| `backends.py` | `HttpBackend`: `POST /v1/systemone`。全体の期限（既定 2 秒）を設け、429 / 529 は期限内で指数バックオフして再試行。レスポンスの型を検証する。`MockBackend`: Jev と同じ形の answers を返すキーワード判定（英語と日本語に対応、**Jev ではない**）。 |
| `policy.py` | answers からモデルを決める純粋関数。作業の種類ごとの基本モデルに、複雑度（noul と score の重み付き和）が 0.6 以上なら1段、1.0 以上なら2段上げる。kind の confidence が 0.5 未満なら1段上げる。noul が 0.5 付近（自信なし）なら「該当あり」とみなす。Haiku は読み取り中心で低リスクの作業に限る。最小・最大モデルの範囲に収める（既定の上限は Opus、Fable は明示的に許可したときだけ） |
| `hook.py` | PreToolUse hook。**どんな失敗でも `JEV_ROUTE_FALLBACK`（既定 sonnet）を明示的に返す**（PoC-1 の知見 3）。fork は対象外。JSONL ログと dry-run モードあり |
| `__main__.py` | 手元で判定を試すための CLI: `python3 -m jevroute "タスク文" -d 説明` |

### バックエンドの切り替え

```bash
JEV_BACKEND=auto   # 既定: TYPESAFE_API_KEY があれば http、なければ mock
JEV_BACKEND=mock
JEV_BACKEND=http   # TYPESAFE_API_KEY 必須。JEV_API_URL / JEV_TIMEOUT_S / JEV_MODEL で調整
```

### Claude Code への組み込み（settings.json）

```json
{"hooks": {"PreToolUse": [{"matcher": "Agent|Task",
  "hooks": [{"type": "command", "command": "cd /path/to/Jev-Agent && python3 -m jevroute.hook"}]}]}}
```

## 検証結果

### 単体テスト（`python3 -m unittest discover -s tests -t .`）: 23件すべて成功

- policy: 種類ごとの基本モデル、複雑度による段上げ、Fable の許可、confidence による段上げ、自信のない noul、Haiku の禁止条件、最小モデル
- HttpBackend（**ローカルの偽 Jev サーバー相手**）: リクエストの形（`state` / `model` / `questions` と Bearer 認証）、429 → 529 → 200 の再試行、期限超過、500 は再試行しない、壊れた JSON、answer の欠落
- hook: モデル以外の入力をそのまま残すこと、バックエンドの失敗や設定ミスでのフォールバック、fork を対象外にすること、dry-run、壊れた標準入力

### エンドツーエンド（`poc2/run_e2e.sh`、メイン会話は Sonnet 5.5）

1つのセッションで「定義ファイルの検索」と「そのファイルのレビュー」を、それぞれ別の Agent に委譲した。どちらも `model` 引数は指定していない。

| ケース | 検索の委譲先 | レビューの委譲先 | 結果 | 総コスト |
|---|---|---|---|---|
| `mock` | **Haiku**（kind=search） | **Opus**（kind=review） | 正しいパスを返し、仕込んだ `eval()` のインジェクションを検出 | $0.274 |
| `unreachable`（接続できない http） | Sonnet（フォールバック） | Sonnet（フォールバック） | 同じく正しい結果。**作業は止まらない** | $0.184 |

- hook の処理時間はモックで約 2ms。実際の Jev は公称 70〜500ms で、期限は 2 秒に設定している。
- 注意: `unreachable` のほうが安く見えるのは、レビューを Opus でなく Sonnet が担当したためで、品質の比較はしていない（どちらも主要な問題は検出した）。「レビューに Opus が必要か」は、PoC-3 の評価で決める。

## 未検証（キー取得後に確認すること）

1. 実際の Jev の判定精度（特に `kind` と、日本語プロンプトのとき）。モックの判定結果は、Jev の精度について何も示していない。
2. 実際のレイテンシと、429 の頻度（レート制限は変動中）。
3. 重み（`WEIGHTS`）としきい値（`BUMP_1/2`）の調整。現在は手で決めた初期値で、PoC-3 の評価で調整する。
4. fork のときの `subagent_type` の実際の値（現在は `fork` と仮定して除外している）。

## キー取得後の手順

```bash
export TYPESAFE_API_KEY=...            # 環境のシークレットとして設定する
python3 -m jevroute "Find where compute_total is defined"   # 1回呼んで、answers とレイテンシを確認
JEV_BACKEND=http ./poc2/run_e2e.sh http
```
