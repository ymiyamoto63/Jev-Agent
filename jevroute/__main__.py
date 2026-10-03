"""Try the router by hand:  python3 -m jevroute "Find where compute_total is defined" [-d description]"""
import argparse
import json

from .hook import route


def main():
    ap = argparse.ArgumentParser(prog="python3 -m jevroute")
    ap.add_argument("task")
    ap.add_argument("-d", "--description", default="")
    ap.add_argument("-t", "--subagent-type", default="general-purpose")
    args = ap.parse_args()
    model, record = route({"prompt": args.task, "description": args.description,
                           "subagent_type": args.subagent_type})
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
