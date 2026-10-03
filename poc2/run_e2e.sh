#!/usr/bin/env bash
# PoC-2 end-to-end: jevroute as the PreToolUse hook inside a real headless Claude Code session.
#   ./run_e2e.sh              -> JEV_BACKEND=mock (no API key needed)
#   ./run_e2e.sh unreachable  -> JEV_BACKEND=http pointed at a dead endpoint: must fall back, not break
#   TYPESAFE_API_KEY=... ./run_e2e.sh http -> real Jev
set -euo pipefail
MODE=${1:-mock}
REPO=$(cd "$(dirname "$0")/.." && pwd)
OUT_DIR=${OUT_DIR:-$REPO/poc2/results}
mkdir -p "$OUT_DIR"
WORK=$(mktemp -d)
export JEV_ROUTE_LOG="$OUT_DIR/route-$MODE.jsonl"
: > "$JEV_ROUTE_LOG"

case "$MODE" in
  mock) export JEV_BACKEND=mock ;;
  unreachable) export JEV_BACKEND=http TYPESAFE_API_KEY=dummy JEV_API_URL=http://127.0.0.1:9/v1/systemone JEV_TIMEOUT_S=1 ;;
  http) export JEV_BACKEND=http ;;
esac

mkdir -p "$WORK/src/billing" "$WORK/src/users"
cat > "$WORK/src/billing/totals.py" <<'PY'
def compute_total(items, discount_code=None):
    total = sum(i.price * i.qty for i in items)
    if discount_code:
        total = total - eval(discount_code)  # applies discount expression
    return round(total, 2)
PY
printf 'def get_user(uid):\n    return {"id": uid}\n' > "$WORK/src/users/repo.py"

cat > "$WORK/settings.json" <<JSON
{"hooks":{"PreToolUse":[{"matcher":"Agent|Task","hooks":[{"type":"command","command":"cd $REPO && python3 -m jevroute.hook"}]}]}}
JSON

PROMPT='Do these two steps in order, each with exactly one Agent tool call (subagent_type "general-purpose", no model argument). Do not do the work yourself.
1. Agent task: "Find which file under src/ defines compute_total and report its path."
2. Agent task: "Review the file found in step 1 for correctness and security problems and list them."
Finally reply with the path and a one-line summary of the review.'

cd "$WORK"
timeout 600 claude -p "$PROMPT" --model sonnet --settings "$WORK/settings.json" \
  --allowedTools "Agent Task Read Glob Grep" --output-format json < /dev/null > "$OUT_DIR/result-$MODE.json"

python3 - "$OUT_DIR/result-$MODE.json" "$JEV_ROUTE_LOG" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("result :", r.get("result", "").strip().replace("\n", " ")[:300])
print("models :")
for m, u in r.get("modelUsage", {}).items():
    print(f"  {m:30s} out={u['outputTokens']:>6} cost=${u['costUSD']:.4f}")
print(f"total  : ${r.get('total_cost_usd', 0):.4f}")
print("routing:")
for line in open(sys.argv[2]):
    d = json.loads(line)
    print(f"  [{d.get('backend', '-')}] {d.get('description')!r:45} -> {d['model']:6} "
          f"{d.get('latency_ms')}ms {d.get('error') or '; '.join(d.get('reasons', []))}")
PY
rm -rf "$WORK"
