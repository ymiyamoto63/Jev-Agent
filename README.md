# Jev-Agent

Jev（TypeSafe System One）で作業内容を判定し、Claude Code のサブエージェントを「十分に足りる最安のモデル」に振り分ける仕組みの検証リポジトリ。

- `docs/feasibility.md` — フィジビリティ検討（結論: 振り分けの単位はサブエージェント。メイン会話のモデルは切り替えない）
- `poc1/` — PreToolUse hook で Agent の `model` を書き換えられることの検証
- `jevroute/` + `poc2/` — Jev ルーター本体（http / mock を差し替え可能）と、エンドツーエンドの検証
- `tools/cost_model.py` — キャッシュを考慮したコスト試算
- `tests/` — `python3 -m unittest discover -s tests -t .`
