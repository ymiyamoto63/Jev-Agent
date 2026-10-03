#!/usr/bin/env python3
"""Run every task on every model with headless Claude Code, grade, and append to a JSONL log.

  python3 eval/run_eval.py                        # all tasks x haiku,sonnet,opus
  python3 eval/run_eval.py --tasks 01-search-env --models haiku
  python3 eval/run_eval.py --check-graders        # no Claude calls: fixture must fail, reference must pass

Each run gets a fresh copy of eval/fixture. Hidden tests are copied in only after the agent finishes.
The Agent tool is disabled so a run's cost and outcome belong to exactly one model.
Re-running skips (task, model) pairs already in the log; use --rerun to force.
"""
import argparse
import concurrent.futures as cf
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from tasks import TASKS  # noqa: E402

FIXTURE = HERE / "fixture"
HIDDEN = HERE / "hidden"
REFERENCE = HERE / "reference"
DEFAULT_LOG = HERE / "results" / "runs.jsonl"
EFFORT = {"sonnet": "medium", "opus": "medium", "fable": "medium"}  # haiku has no effort setting


def fresh_workdir():
    d = Path(tempfile.mkdtemp(prefix="jeveval-"))
    shutil.copytree(FIXTURE, d, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
    return d


def grade(task, workdir, answer):
    g, checks = task["grade"], {}
    for i, pat in enumerate(g.get("answer", [])):
        checks[f"answer[{i}]"] = bool(re.search(pat, answer or "", re.I | re.M))
    if "absent" in g:
        hits = [str(p.relative_to(workdir)) for base in ("shop", "tests") for p in (workdir / base).rglob("*.py")
                if re.search(g["absent"], p.read_text(errors="replace"))]
        checks["absent"] = not hits
    if "present" in g:
        path, pat = g["present"]
        f = workdir / path
        checks["present"] = f.exists() and bool(re.search(pat, f.read_text(errors="replace")))
    if "tests" in g:
        name = "hidden_" + g["tests"]
        shutil.copy(HIDDEN / g["tests"], workdir / "tests" / name)
        r = subprocess.run([sys.executable, "-m", "unittest", f"tests.{name[:-3]}"], cwd=workdir,
                           capture_output=True, text=True, timeout=120)
        checks["tests"] = r.returncode == 0
        if r.returncode:
            checks["tests_output"] = r.stderr[-1500:]
    passed = all(v for k, v in checks.items() if k != "tests_output")
    return passed, checks


def run_one(task, model, timeout_s):
    workdir = fresh_workdir()
    cmd = ["claude", "-p", task["prompt"], "--model", model, "--output-format", "json",
           "--allowedTools", "Read Edit Write Glob Grep Bash",
           "--disallowedTools", "Agent Task",
           "--no-session-persistence"]
    if model in EFFORT:
        cmd += ["--effort", EFFORT[model]]
    started = time.time()
    rec = {"task": task["id"], "kind": task["kind"], "lang": task["lang"], "model": model, "started": started}
    try:
        p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=timeout_s, stdin=subprocess.DEVNULL)
        out = json.loads(p.stdout)
        answer = out.get("result", "")
        rec.update(cost_usd=out.get("total_cost_usd"), num_turns=out.get("num_turns"),
                   duration_ms=out.get("duration_ms"), is_error=out.get("is_error"),
                   models_used=sorted(out.get("modelUsage", {})),
                   output_tokens=sum(u.get("outputTokens", 0) for u in out.get("modelUsage", {}).values()),
                   answer=answer[-2000:])
    except subprocess.TimeoutExpired:
        answer, rec["error"] = "", "timeout"
    except (json.JSONDecodeError, OSError) as e:
        answer, rec["error"] = "", f"{type(e).__name__}: {e}; stderr={p.stderr[-500:] if 'p' in dir() else ''}"
    rec["passed"], rec["checks"] = grade(task, workdir, answer)
    rec["wall_s"] = round(time.time() - started, 1)
    shutil.rmtree(workdir, ignore_errors=True)
    return rec


def check_graders():
    """Fixture as-is must fail every task; fixture + reference solution must pass every task."""
    ok = True
    for t in TASKS:
        wd = fresh_workdir()
        base, _ = grade(t, wd, "")
        shutil.rmtree(wd)
        wd = fresh_workdir()
        ref = REFERENCE / t["id"]
        answer = ""
        if ref.exists():
            for f in ref.rglob("*"):
                if f.is_file() and f.name != "answer.txt":
                    dst = wd / f.relative_to(ref)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(f, dst)
            if (ref / "answer.txt").exists():
                answer = (ref / "answer.txt").read_text()
        good, checks = grade(t, wd, answer)
        shutil.rmtree(wd)
        status = "OK " if (not base and good) else "BAD"
        ok &= status == "OK "
        print(f"{status} {t['id']:22} baseline_pass={base} reference_pass={good}"
              + ("" if good else f"  {checks}"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="haiku,sonnet,opus")
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--check-graders", action="store_true")
    args = ap.parse_args()

    if args.check_graders:
        sys.exit(0 if check_graders() else 1)

    log = Path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if log.exists() and not args.rerun:
        done = {(r["task"], r["model"]) for r in map(json.loads, log.read_text().splitlines()) if "error" not in r}
    tasks = TASKS if args.tasks == "all" else [t for t in TASKS if t["id"] in args.tasks.split(",")]
    jobs = [(t, m) for t in tasks for m in args.models.split(",") if (t["id"], m) not in done]
    print(f"{len(jobs)} runs ({len(done)} already logged)")

    with cf.ThreadPoolExecutor(args.parallel) as ex, log.open("a") as f:
        futs = {ex.submit(run_one, t, m, args.timeout): (t["id"], m) for t, m in jobs}
        for fut in cf.as_completed(futs):
            rec = fut.result()
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            print(f"{'PASS' if rec['passed'] else 'FAIL'} {rec['task']:22} {rec['model']:6} "
                  f"${rec.get('cost_usd') or 0:.3f} {rec['wall_s']}s {rec.get('error', '')}", flush=True)


if __name__ == "__main__":
    main()
