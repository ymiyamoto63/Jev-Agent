#!/usr/bin/env python3
"""Replay routers over recorded runs: no new Claude calls.

For each task the "label" is the cheapest model that passed. Each router picks a model per task;
its outcome and cost are looked up from the log. "+esc" variants escalate one tier after a failure
(haiku -> sonnet -> opus) and pay for every attempt. This assumes failure is detectable (tests),
which is optimistic for review/search tasks.

  python3 eval/analyze.py                      # mock backend for jevroute
  JEV_BACKEND=http python3 eval/analyze.py     # real Jev (decisions cached in results/decisions-http.json)
"""
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from tasks import TASKS  # noqa: E402

from jevroute.backends import get_backend  # noqa: E402
from jevroute.policy import decide  # noqa: E402
from jevroute.questions import build_request, build_state  # noqa: E402

TIERS = ["haiku", "sonnet", "opus"]


def load_runs(path):
    runs = {}
    for line in Path(path).read_text().splitlines():
        r = json.loads(line)
        runs[(r["task"], r["model"])] = r  # last record wins
    return runs


def keyword_router():
    spec = importlib.util.spec_from_file_location("poc1_route", ROOT / "poc1" / "hooks" / "route_agent.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return lambda t: mod.route({"prompt": t["prompt"], "description": ""})


def jev_router(cache_path):
    backend = get_backend()
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    def route(t):
        if t["id"] not in cache:
            answers, raw = backend.ask(build_request(build_state({"prompt": t["prompt"], "subagent_type": "general-purpose"})))
            cache[t["id"]] = {"answers": answers, "usage": raw.get("usage")}
            cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
        d = decide(cache[t["id"]]["answers"])
        return min(d.model, "opus", key=TIERS.index) if d.model in TIERS else "opus"
    return backend.name, route


def simulate(choose, runs, escalate):
    rows = []
    for t in TASKS:
        model = choose(t)
        cost, passed, tried = 0.0, False, []
        i = TIERS.index(model)
        while True:
            r = runs.get((t["id"], TIERS[i]))
            if r is None:
                break
            cost += r.get("cost_usd") or 0
            tried.append(TIERS[i])
            passed = r["passed"]
            if passed or not escalate or i == len(TIERS) - 1:
                break
            i += 1
        rows.append({"task": t["id"], "chosen": model, "tried": tried, "passed": passed, "cost": cost})
    return rows


def main():
    log = sys.argv[1] if len(sys.argv) > 1 else HERE / "results" / "runs.jsonl"
    runs = load_runs(log)
    out = []

    # --- per-task matrix and labels
    labels = {}
    out.append("## Per-task results (pass / cost USD)\n")
    out.append("| task | kind | lang | " + " | ".join(TIERS) + " | label (cheapest pass) |")
    out.append("|---|---|---|" + "---|" * len(TIERS) + "---|")
    for t in TASKS:
        cells, label = [], "none"
        for m in TIERS:
            r = runs.get((t["id"], m))
            if r is None:
                cells.append("—")
                continue
            cells.append(f"{'✅' if r['passed'] else '❌'} ${r.get('cost_usd') or 0:.3f}")
            if r["passed"] and label == "none":
                label = m
        labels[t["id"]] = label
        out.append(f"| {t['id']} | {t['kind']} | {t['lang']} | " + " | ".join(cells) + f" | **{label}** |")

    by_kind = defaultdict(list)
    for t in TASKS:
        by_kind[t["kind"]].append(labels[t["id"]])
    out.append("\n## Labels by kind\n")
    for k, v in by_kind.items():
        out.append(f"- {k}: {', '.join(v)}")

    # --- routers
    routers = {f"all-{m}": (lambda m: lambda t: m)(m) for m in TIERS}
    routers["oracle"] = lambda t: labels[t["id"]] if labels[t["id"]] != "none" else "opus"
    routers["keyword (PoC-1)"] = keyword_router()
    name, jr = jev_router(HERE / "results" / f"decisions-{get_backend().name}.json")
    routers[f"jevroute ({name})"] = jr

    out.append("\n## Router comparison\n")
    out.append("| router | success | total cost | cost / success | under-routed | over-routed | choices |")
    out.append("|---|---|---|---|---|---|---|")
    details = {}
    for rname, choose in routers.items():
        for esc in (False, True):
            if esc and rname.startswith(("all-opus", "oracle")):
                continue
            rows = simulate(choose, runs, esc)
            ok = sum(r["passed"] for r in rows)
            cost = sum(r["cost"] for r in rows)
            under = sum(1 for r in rows if labels[r["task"]] != "none" and TIERS.index(r["chosen"]) < TIERS.index(labels[r["task"]]))
            over = sum(1 for r in rows if labels[r["task"]] != "none" and TIERS.index(r["chosen"]) > TIERS.index(labels[r["task"]]))
            choices = {m: sum(r["chosen"] == m for r in rows) for m in TIERS}
            label = rname + (" +esc" if esc else "")
            details[label] = rows
            out.append(f"| {label} | {ok}/{len(rows)} | ${cost:.2f} | ${cost / max(ok, 1):.3f} | {under} | {over} | "
                       + " ".join(f"{m[0].upper()}{c}" for m, c in choices.items()) + " |")

    jname = f"jevroute ({name})"
    out.append(f"\n## {jname}: per-task decisions\n")
    out.append("| task | label | chosen | passed | +esc tried |")
    out.append("|---|---|---|---|---|")
    for r, re_ in zip(details[jname], details[jname + " +esc"]):
        out.append(f"| {r['task']} | {labels[r['task']]} | {r['chosen']} | {'✅' if r['passed'] else '❌'} | {'→'.join(re_['tried'])} |")

    report = "\n".join(out)
    (HERE / "results" / "report.md").write_text(report + "\n")
    print(report)


if __name__ == "__main__":
    main()
