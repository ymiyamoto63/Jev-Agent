#!/usr/bin/env python3
"""PoC-1: PreToolUse hook that rewrites the Agent tool's `model` parameter.

No Jev yet: a fixed keyword rule stands in for the router, so this only proves the mechanism.
Every decision is appended to $ROUTE_LOG (JSONL) for inspection.
"""
import json
import os
import re
import sys

RULES = [
    ("haiku", re.compile(r"\b(search|find|grep|locate|list|read|look up)\b", re.I)),
    ("opus", re.compile(r"\b(design|architecture|review|requirements?)\b", re.I)),
]
DEFAULT = "sonnet"


def route(tool_input):
    text = f"{tool_input.get('description', '')}\n{tool_input.get('prompt', '')}"
    for model, pattern in RULES:
        if pattern.search(text):
            return model
    return DEFAULT


def main():
    event = json.load(sys.stdin)
    tool_input = event.get("tool_input", {})
    chosen = route(tool_input)

    log_path = os.environ.get("ROUTE_LOG")
    if log_path:
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "tool_name": event.get("tool_name"),
                "requested_model": tool_input.get("model"),
                "chosen_model": chosen,
                "subagent_type": tool_input.get("subagent_type"),
                "description": tool_input.get("description"),
                "input_keys": sorted(tool_input),
            }) + "\n")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {**tool_input, "model": chosen},
        }
    }
    if os.environ.get("ROUTE_ALLOW") == "1":
        output["hookSpecificOutput"]["permissionDecision"] = "allow"
    json.dump(output, sys.stdout)


if __name__ == "__main__":
    main()
