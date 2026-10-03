"""20 evaluation tasks over eval/fixture. Each prompt is written the way a main agent would delegate it.

`kind` is our own label (for analysis), not an input to any router.
Graders:
  answer:  every regex must match the agent's final reply (case-insensitive)
  tests:   hidden unittest file copied in AFTER the run, must pass
  absent:  regex must not occur in any *.py file under shop/ and tests/
  present: (path, regex) must occur in that file
"""

DIFF_19 = """--- a/shop/inventory.py
+++ b/shop/inventory.py
@@ def reserve(self, sku, qty):
-        available = self._stock.get(sku, 0)
-        if qty > available:
+        remaining = self._stock.get(sku, 0)
+        if qty >= remaining:
             raise OutOfStock(sku)
         with self._audit_lock:
             self._on_reserve(sku, qty)
-        self._stock[sku] = available - qty
+        self._stock[sku] = remaining - qty
         return self._stock[sku]"""

TASKS = [
    # --- search -------------------------------------------------------------
    dict(id="01-search-env", lang="en", kind="search",
         prompt="Which file and function read the SHOP_PAGE_SIZE environment variable? Answer as `path:function`. Do not modify any files.",
         grade={"answer": [r"shop/config\.py", r"load_config"]}),
    dict(id="02-search-callers", lang="ja", kind="search",
         prompt="shop/ 配下で compute_total を呼び出している箇所（ファイルと関数・メソッド名）をすべて挙げてください。ファイルは変更しないでください。",
         grade={"answer": [r"orders\.py", r"cli\.py", r"\btotal\b", r"\bmain\b"]}),
    dict(id="03-search-exception", lang="en", kind="search",
         prompt="Which module defines the exception raised when stock runs out, and which method raises it? Do not modify any files.",
         grade={"answer": [r"inventory", r"OutOfStock", r"reserve"]}),
    # --- test_run -----------------------------------------------------------
    dict(id="04-run-tests", lang="ja", kind="test_run",
         prompt="テストスイート（python3 -m unittest discover -s tests -t .）を実行し、失敗またはエラーになったテストの名前を報告してください。コードは変更しないでください。",
         grade={"answer": [r"test_add_months_end_of_month"]}),
    dict(id="05-run-cli", lang="en", kind="test_run",
         prompt="Run `python3 -m shop.cli stats` and report the inventory value it prints. Do not modify any files.",
         grade={"answer": [r"1,?401\.85"]}),
    # --- mechanical_edit ----------------------------------------------------
    dict(id="06-rename", lang="en", kind="mechanical_edit",
         prompt="Rename the function `search_products` to `find_products` everywhere in the codebase (definition, call sites, tests). Keep behavior identical.",
         grade={"tests": "test_rename.py", "absent": r"search_products"}),
    dict(id="07-typo", lang="ja", kind="mechanical_edit",
         prompt="shop/orders.py のエラーメッセージ \"Invalid quantitiy\" の誤字を \"Invalid quantity\" に修正してください。",
         grade={"absent": r"quantitiy", "present": ["shop/orders.py", r"Invalid quantity"]}),
    dict(id="08-page-size", lang="en", kind="mechanical_edit",
         prompt="Change the default page size from 20 to 25 and update the existing test that checks the default.",
         grade={"tests": "test_page_size.py", "present": ["tests/test_config.py", r"25"]}),
    # --- feature ------------------------------------------------------------
    dict(id="09-cli-json", lang="en", kind="feature",
         prompt="Add a `--json` flag to the `list` command in shop/cli.py. With the flag, print a JSON array of the matching products, "
                "each an object with keys sku, name, price (number). Without the flag, output must stay exactly as it is today.",
         grade={"tests": "test_cli_json.py"}),
    dict(id="10-validation", lang="ja", kind="feature",
         prompt="shop/catalog.py の Product に入力検証を追加してください。price が負なら ValueError、sku が「英大文字3文字-数字4桁」"
                "（例: ABC-0001）の形式でなければ ValueError を送出すること。price が 0 は許可します。既存の PRODUCTS はそのまま有効であること。",
         grade={"tests": "test_validation.py"}),
    dict(id="11-pricing", lang="en", kind="feature",
         prompt="""Create shop/pricing.py with `price_order(lines, customer_tier, coupon=None) -> decimal.Decimal`.
`lines` is a list of (sku, unit_price, qty) where unit_price is a decimal string like "12.50".
Rules, applied in this order:
1. Volume discount per line: qty >= 50 -> 10% off that line; else qty >= 10 -> 5% off. Round each line to cents (half-up).
2. Tier discount on the sum of lines: "gold" 3%, "platinum" 5%, anything else 0%. Round to cents (half-up).
3. Coupon "SAVE10": subtract 10.00, only if the amount after step 2 is >= 50.00. The amount never goes below 0.
4. Shipping: add 7.00 if the amount after step 3 is below 100.00, unless coupon is "FREESHIP".
Return a Decimal quantized to 0.01 (half-up). Use Decimal arithmetic throughout.""",
         grade={"tests": "test_pricing.py"}),
    dict(id="12-ttl-cache", lang="ja", kind="feature",
         prompt="""shop/cache.py に TTL 付き LRU キャッシュのデコレータ `ttl_lru_cache(maxsize=128, ttl=60.0, clock=time.monotonic)` を実装してください。
- 引数（位置引数とキーワード引数の両方）をキーに結果をキャッシュする
- 保存から ttl 秒以上経過したエントリは期限切れ（ちょうど ttl 秒も期限切れ）
- maxsize を超えたら最も長く使われていないエントリを破棄（ヒットしたアクセスも「使用」に含む）
- ラップした関数に cache_info() -> {"hits": int, "misses": int, "size": int} と cache_clear()（統計もリセット）を付ける
- clock はテストで差し替えられるようにする""",
         grade={"tests": "test_cache.py"}),
    # --- debug --------------------------------------------------------------
    dict(id="13-paginate", lang="en", kind="debug",
         prompt="Users report that page 1 of the product list shows the second page of results. Find and fix the bug.",
         grade={"tests": "test_paginate.py"}),
    dict(id="14-add-months", lang="ja", kind="debug",
         prompt="add_months が月末日（例: 1月31日 + 1か月）で例外になります。存在しない日になる場合は、その月の末日に丸めるよう修正してください。負の月数にも対応すること。",
         grade={"tests": "test_add_months.py"}),
    dict(id="15-rounding", lang="en", kind="debug",
         prompt="Some invoice totals are off by one cent compared to our accounting system, which rounds half-up "
                "(e.g. a 1.15 item with a 50% discount should cost 0.58, we return 0.57). Fix compute_total.",
         grade={"tests": "test_rounding.py"}),
    dict(id="16-race", lang="ja", kind="debug",
         prompt="本番で在庫の過剰引当が発生しています（在庫 10 なのに 10 件を超える予約が成功する）。StockCounter.reserve は複数スレッドから同時に呼ばれ、"
                "on_reserve の監査フックは本番では DB 書き込みを行います。原因を特定して修正してください。",
         grade={"tests": "test_race.py"}),
    dict(id="17-double-discount", lang="en", kind="debug",
         prompt="Customers using a coupon are charged less than they should be at checkout (TENOFF on a 100.00 order charges 81.00). "
                "Find the root cause and fix it without changing Order.total().",
         grade={"tests": "test_checkout.py"}),
    # --- review -------------------------------------------------------------
    dict(id="18-security-review", lang="ja", kind="review",
         prompt="shop/ パッケージのセキュリティレビューを行い、脆弱性をファイル名・関数名とともに列挙してください。コードは変更しないでください。",
         grade={"answer": [r"SQL", r"find_by_customer", r"eval", r"calc_discount"]}),
    dict(id="19-diff-review", lang="en", kind="review",
         prompt="Review this proposed change to shop/inventory.py. Start your reply with exactly BUG or OK, then explain. "
                "Do not modify any files.\n\n" + DIFF_19,
         grade={"answer": [r"^\W*BUG", r">=|equal|exact|remaining|last|all of the|entire"]}),
    # --- design -------------------------------------------------------------
    dict(id="20-event-bus", lang="ja", kind="design",
         prompt="""shop/events.py に同期イベントバス EventBus を設計・実装してください。要件:
- subscribe(event, handler, priority=0, once=False) は購読解除用の関数を返す（何度呼んでも安全）
- publish(event, payload) は priority の高い順、同じ priority なら登録順に handler(payload) を呼び、呼んだ handler の数を返す
- once=True の handler は最初の 1 回だけ呼ばれる
- ディスパッチ中に購読解除が起きても、その回の他の handler は飛ばされない
- handler の例外で他の handler の実行を止めない。全 handler 実行後、発生した例外をまとめて ExceptionGroup で送出する""",
         grade={"tests": "test_events.py"}),
]

assert len(TASKS) == 20 and len({t["id"] for t in TASKS}) == 20
