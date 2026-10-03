"""Jev backends. Everything above this module sees only Jev-shaped `answers` dicts.

  JEV_BACKEND=http  -> TypeSafe API (needs TYPESAFE_API_KEY)
  JEV_BACKEND=mock  -> local keyword heuristic that imitates Jev's response shape. NOT Jev:
                       it exists to exercise the pipeline before an API key is available.
  JEV_BACKEND=auto  -> http if TYPESAFE_API_KEY is set, else mock (default)
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from .questions import KINDS, QUESTIONS

API_URL = "https://api.typesafe.ai/v1/systemone"
RETRY_STATUS = {429, 529}


class BackendError(Exception):
    pass


def validate_answers(answers):
    """Fail loudly on anything policy.py can't consume, so the hook falls back instead of guessing."""
    for key, q in QUESTIONS.items():
        a = answers.get(key)
        if not isinstance(a, dict) or a.get("type") != q["type"]:
            raise BackendError(f"missing or mistyped answer: {key}")
        if q["type"] == "choice" and (a.get("choice") not in q["criteria"] or "confidence" not in a):
            raise BackendError(f"bad choice answer: {key}")
        if q["type"] == "noul" and not isinstance(a.get("noul"), (int, float)):
            raise BackendError(f"bad noul answer: {key}")
        if q["type"] == "score" and not isinstance(a.get("score"), (int, float)):
            raise BackendError(f"bad score answer: {key}")
    return answers


class HttpBackend:
    name = "http"

    def __init__(self, api_key, url=API_URL, deadline_s=2.0, model="jev-latest"):
        self.api_key, self.url, self.deadline_s, self.model = api_key, url, deadline_s, model

    def ask(self, request):
        body = json.dumps({**request, "model": self.model}).encode()
        start = time.monotonic()
        backoff = 0.1
        while True:
            remaining = self.deadline_s - (time.monotonic() - start)
            if remaining <= 0:
                raise BackendError("deadline exceeded")
            req = urllib.request.Request(self.url, data=body, method="POST", headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
            try:
                with urllib.request.urlopen(req, timeout=remaining) as resp:
                    payload = json.load(resp)
                return validate_answers(payload["answers"]), payload
            except urllib.error.HTTPError as e:
                if e.code in RETRY_STATUS and time.monotonic() - start + backoff < self.deadline_s:
                    retry_after = e.headers.get("retry-after")
                    time.sleep(min(float(retry_after), backoff * 4) if retry_after else backoff)
                    backoff *= 2
                    continue
                raise BackendError(f"HTTP {e.code}") from e
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
                raise BackendError(f"{type(e).__name__}: {e}") from e


# --- mock -------------------------------------------------------------------

_KIND_PATTERNS = {
    "search": r"\b(find|search|locate|grep|look ?up|list|where is|read|summari[sz]e|explore)\b|探し|検索|調べ|一覧|読ん|要約",
    "test_run": r"\b(run (the )?(tests?|build|suite)|execute tests?|pytest|npm test)\b|テストを実行|ビルドを実行",
    "mechanical_edit": r"\b(rename|typo|format|bump|lint fix|update the version)\b|リネーム|誤字|整形",
    "feature": r"\b(implement|add (a |an )?(feature|endpoint|option|support)|build|create)\b|実装|追加|作成",
    "debug": r"\b(fix|debug|bug|failing|error|crash|regression)\b|修正|バグ|不具合|エラー",
    "review": r"\b(review|audit|check (the )?(diff|changes))\b|レビュー|監査",
    "design": r"\b(design|architecture|requirements?|plan|propose|trade-?offs?)\b|設計|要件|方針",
}
_SIGNALS = {
    "edits_code": r"\b(implement|add|create|fix|rename|modify|change|update|write|refactor)\b|実装|追加|修正|変更|作成|書",
    "multi_module": r"\b(across|multiple|all (the )?(modules|services|packages)|end-to-end|refactor)\b|横断|複数|全体",
    "ambiguous": r"\b(somehow|something like|maybe|figure out|improve|better)\b|いい感じ|なんとか|改善",
    "risky_domain": r"\b(auth\w*|security|password|token|concurren\w*|race|migration|payment|billing|delete|drop)\b|認証|セキュリティ|並行|移行|決済|削除",
}
_NOVEL = r"\b(design|architecture|root cause|intermittent|race|trade-?offs?|novel|algorithm)\b|設計|根本原因|アルゴリズム"
_TRIVIAL = r"\b(find|list|rename|typo|run|read|where)\b|探し|一覧|実行|読"


def _choice_answer(probs):
    n = len(probs)
    top = max(probs, key=probs.get)
    conf = (probs[top] - 1 / n) / (1 - 1 / n)
    return {"type": "choice", "choice": top, "probabilities": probs, "confidence": round(conf, 3)}


class MockBackend:
    """Keyword heuristic in Jev's response shape. Deterministic; for plumbing tests only."""
    name = "mock"

    def ask(self, request):
        state = request["state"]
        text = f"{state.get('summary', '')}\n{state.get('task', '')}" if isinstance(state, dict) else str(state)

        hits = {k: len(re.findall(p, text, re.I)) for k, p in _KIND_PATTERNS.items()}
        total = sum(hits.values())
        if total == 0:
            probs = {k: 1 / len(KINDS) for k in KINDS}
        else:
            smooth = 0.05
            raw = {k: hits.get(k, 0) + smooth for k in KINDS}
            z = sum(raw.values())
            probs = {k: round(v / z, 4) for k, v in raw.items()}

        answers = {"kind": _choice_answer(probs)}
        for key, pattern in _SIGNALS.items():
            answers[key] = {"type": "noul", "noul": 0.9 if re.search(pattern, text, re.I) else 0.1}

        legend = {str(i): c for i, c in enumerate(QUESTIONS["novelty"]["criteria"])}
        if re.search(_NOVEL, text, re.I):
            level = 2
        elif re.search(_TRIVIAL, text, re.I):
            level = 0
        else:
            level = 1
        lp = {str(i): (0.9 if i == level else 0.05) for i in range(3)}
        answers["novelty"] = {"type": "score", "score": float(level), "legend": legend,
                              "probabilities": lp, "confidence": 0.85}
        return validate_answers(answers), {"model": "mock", "answers": answers}


def get_backend(env=None):
    env = os.environ if env is None else env
    choice = env.get("JEV_BACKEND", "auto")
    key = env.get("TYPESAFE_API_KEY")
    if choice == "mock" or (choice == "auto" and not key):
        return MockBackend()
    if not key:
        raise BackendError("JEV_BACKEND=http but TYPESAFE_API_KEY is not set")
    return HttpBackend(
        api_key=key,
        url=env.get("JEV_API_URL", API_URL),
        deadline_s=float(env.get("JEV_TIMEOUT_S", "2.0")),
        model=env.get("JEV_MODEL", "jev-latest"),
    )
