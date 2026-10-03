"""Claude Code PreToolUse hook (matcher: Agent|Task): set the subagent's model from Jev's judgment.

Never blocks the Agent call. Any failure (no key, timeout, bad response) falls back to
JEV_ROUTE_FALLBACK explicitly, because a crashed hook would leave the caller's model in place.

Env:
  JEV_BACKEND            auto | http | mock          (see backends.py)
  JEV_ROUTE_MIN_MODEL    lowest model to assign      (default haiku)
  JEV_ROUTE_MAX_MODEL    highest model to assign     (default opus)
  JEV_ROUTE_FALLBACK     model when routing fails    (default sonnet)
  JEV_ROUTE_SKIP_TYPES   comma list of subagent_type values left untouched (default: fork)
  JEV_ROUTE_LOG          JSONL decision log path     (default: none)
  JEV_ROUTE_DRY_RUN=1    log decisions but don't change the model
"""
import json
import os
import sys
import time

from . import MODELS
from .backends import get_backend
from .policy import Config, decide
from .questions import build_request, build_state


def config_from_env(env):
    cfg = Config(
        min_model=env.get("JEV_ROUTE_MIN_MODEL", "haiku"),
        max_model=env.get("JEV_ROUTE_MAX_MODEL", "opus"),
        fallback_model=env.get("JEV_ROUTE_FALLBACK", "sonnet"),
    )
    for m in (cfg.min_model, cfg.max_model, cfg.fallback_model):
        if m not in MODELS:
            raise ValueError(f"unknown model {m!r}; expected one of {MODELS}")
    return cfg


def route(tool_input, env=None):
    """Returns (model or None to leave untouched, log record)."""
    env = os.environ if env is None else env
    record = {"ts": time.time(), "subagent_type": tool_input.get("subagent_type"),
              "requested_model": tool_input.get("model"), "description": tool_input.get("description")}

    skip = {s.strip() for s in env.get("JEV_ROUTE_SKIP_TYPES", "fork").split(",") if s.strip()}
    if tool_input.get("subagent_type") in skip:
        record["skipped"] = True
        return None, record

    fallback = env.get("JEV_ROUTE_FALLBACK", "sonnet")
    start = time.monotonic()
    try:
        cfg = config_from_env(env)
        backend = get_backend(env)
        record["backend"] = backend.name
        answers, raw = backend.ask(build_request(build_state(tool_input)))
        decision = decide(answers, cfg)
        record.update(model=decision.model, kind=decision.kind, complexity=decision.complexity,
                      reasons=decision.reasons, jev_usage=raw.get("usage"))
        model = decision.model
    except Exception as e:  # never break the Agent call
        record.update(model=fallback, error=f"{type(e).__name__}: {e}")
        model = fallback
    record["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
    return model, record


def main(stdin=sys.stdin, stdout=sys.stdout, env=None):
    env = os.environ if env is None else env
    try:
        event = json.load(stdin)
    except ValueError:
        return 0  # nothing we can do; let the call through unchanged
    tool_input = event.get("tool_input") or {}
    model, record = route(tool_input, env)

    log_path = env.get("JEV_ROUTE_LOG")
    if log_path:
        try:
            with open(log_path, "a") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

    if model is None or env.get("JEV_ROUTE_DRY_RUN") == "1":
        return 0
    json.dump({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "updatedInput": {**tool_input, "model": model},
    }}, stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
