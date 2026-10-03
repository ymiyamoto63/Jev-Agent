#!/usr/bin/env bash
# PoC-1 runner: does a PreToolUse hook's updatedInput.model change the model a subagent runs on?
#   ./run_poc.sh control  -> no hook (subagent should run on the model the main agent asked for: opus)
#   ./run_poc.sh hook     -> hook rewrites model by keyword rule (search task -> haiku)
#   ROUTE_ALLOW=1 ./run_poc.sh hook  -> same, with permissionDecision=allow added
set -euo pipefail
MODE=${1:-hook}
HERE=$(cd "$(dirname "$0")" && pwd)
WORK=$(mktemp -d)
OUT_DIR=${OUT_DIR:-$HERE/results}
mkdir -p "$OUT_DIR"
TAG="$MODE-${VARIANT:-explicit}"
export ROUTE_LOG="$OUT_DIR/route-$TAG.jsonl"
: > "$ROUTE_LOG"

# tiny fixture repo
mkdir -p "$WORK/src/billing" "$WORK/src/users"
printf 'def compute_total(items):\n    return sum(i.price for i in items)\n' > "$WORK/src/billing/totals.py"
printf 'def get_user(uid):\n    return {"id": uid}\n' > "$WORK/src/users/repo.py"
printf '# fixture\n' > "$WORK/README.md"

if [ "$MODE" = broken ]; then
  # hook that crashes: does the Agent call still go through with the original input?
  echo '{"hooks":{"PreToolUse":[{"matcher":"Agent|Task","hooks":[{"type":"command","command":"python3 -c \\"raise SystemExit(1)\\""}]}]}}' > "$WORK/settings.json"
elif [ "$MODE" = hook ]; then
  cat > "$WORK/settings.json" <<JSON
{"hooks":{"PreToolUse":[{"matcher":"Agent|Task","hooks":[{"type":"command","command":"python3 $HERE/hooks/route_agent.py"}]}]}}
JSON
else
  echo '{}' > "$WORK/settings.json"
fi

TASK='"Find which file under src/ defines the function compute_total and report its path."'
TAIL='Do not search yourself. After the subagent returns, reply with only the path.'
case "${VARIANT:-explicit}" in
  explicit) PROMPT="Call the Agent tool exactly once, with subagent_type \"general-purpose\" and model \"opus\", and this task: $TASK $TAIL" ;;
  # no model argument at all; built-in Explore agent (runs on Opus by default on the Anthropic API)
  nomodel)  PROMPT="Call the Agent tool exactly once, with subagent_type \"Explore\" and no model argument, and this task: $TASK $TAIL" ;;
  # custom agent whose frontmatter pins model: opus
  frontmatter)
    mkdir -p "$WORK/.claude/agents"
    printf -- '---\nname: finder\ndescription: Locates code in the repo\nmodel: opus\n---\nYou locate code and report file paths.\n' > "$WORK/.claude/agents/finder.md"
    PROMPT="Call the Agent tool exactly once, with subagent_type \"finder\" and no model argument, and this task: $TASK $TAIL" ;;
esac

cd "$WORK"
timeout 300 claude -p "$PROMPT" --model sonnet --settings "$WORK/settings.json" \
  --allowedTools "Agent Task Read Glob Grep Bash" --output-format json < /dev/null > "$OUT_DIR/result-$TAG.json"

python3 - "$OUT_DIR/result-$TAG.json" "$ROUTE_LOG" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("result      :", r.get("result", "").strip()[:200])
print("models used :")
for m, u in r.get("modelUsage", {}).items():
    print(f"  {m:32s} out={u['outputTokens']:>6} cost=${u['costUSD']:.4f}")
print("subagents   :", {k: r.get("subagent_stats", {}).get(k) for k in ("spawned", "completed", "failed")})
print("hook log    :")
for line in open(sys.argv[2]):
    print("  ", line.strip())
PY
rm -rf "$WORK"
