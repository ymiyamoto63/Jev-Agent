import argparse

from .catalog import PRODUCTS, in_stock, search_products
from .money import LineItem, compute_total, format_price


def main(argv=None):
    ap = argparse.ArgumentParser(prog="shop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--query", default="")
    ls.add_argument("--json", action="store_true")
    sub.add_parser("stats")
    args = ap.parse_args(argv)

    if args.cmd == "list":
        found = search_products(args.query)
        if args.json:
            import json
            print(json.dumps([{"sku": p.sku, "name": p.name, "price": p.price} for p in found]))
            return 0
        for p in found:
            print(f"{p.sku}  {p.name:<15} {format_price(p.price)}")
    elif args.cmd == "stats":
        stocked = in_stock()
        value = compute_total([LineItem(p.price, p.stock) for p in stocked])
        print(f"products in stock: {len(stocked)}")
        print(f"inventory value: {format_price(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
