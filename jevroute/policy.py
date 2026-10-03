"""Turn Jev answers into a model choice. Pure functions: no I/O, fully unit-testable.

Composite scoring (docs.typesafe.ai/patterns/composite-scoring): a base model per kind of work,
bumped up by escalation signals and by low confidence. Under-routing costs a failed run plus
a retry, so every uncertainty resolves upward.
"""
from dataclasses import dataclass, field

from . import MODELS

BASE_MODEL = {
    "search": "haiku",
    "test_run": "haiku",
    "mechanical_edit": "haiku",
    "feature": "sonnet",
    "debug": "sonnet",
    "review": "opus",
    "design": "opus",
}

WEIGHTS = {"multi_module": 0.35, "ambiguous": 0.25, "risky_domain": 0.45, "novelty": 0.5}
BUMP_1 = 0.6   # complexity >= this -> one tier up
BUMP_2 = 1.0   # complexity >= this -> two tiers up
KIND_CONFIDENCE_FLOOR = 0.5  # docs: 0.5 catches answers the model reports as genuinely uncertain
NOUL_UNSURE = 0.3            # |2p-1| below this = Jev is unsure; treat the signal as present


@dataclass
class Config:
    min_model: str = "haiku"
    max_model: str = "opus"      # fable only when explicitly allowed
    fallback_model: str = "sonnet"


@dataclass
class Decision:
    model: str
    kind: str | None = None
    complexity: float | None = None
    reasons: list = field(default_factory=list)


def noul_confidence(p):
    return abs(2 * p - 1)


def _tier(model):
    return MODELS.index(model)


def _clamp(tier, cfg):
    return max(_tier(cfg.min_model), min(_tier(cfg.max_model), tier))


def decide(answers, cfg=None):
    cfg = cfg or Config()
    reasons = []

    kind_ans = answers["kind"]
    kind = kind_ans["choice"]
    tier = _tier(BASE_MODEL.get(kind, cfg.fallback_model))
    reasons.append(f"kind={kind} (conf {kind_ans['confidence']:.2f}) -> base {MODELS[tier]}")

    signals = {}
    for key in ("multi_module", "ambiguous", "risky_domain"):
        p = answers[key]["noul"]
        if noul_confidence(p) < NOUL_UNSURE:
            p = max(p, 0.5)  # unsure counts as present
        signals[key] = p
    novelty = answers["novelty"]
    levels = len(novelty.get("legend") or {}) or 3
    signals["novelty"] = novelty["score"] / (levels - 1)

    complexity = sum(WEIGHTS[k] * v for k, v in signals.items())
    if complexity >= BUMP_2:
        tier += 2
        reasons.append(f"complexity {complexity:.2f} >= {BUMP_2}: +2")
    elif complexity >= BUMP_1:
        tier += 1
        reasons.append(f"complexity {complexity:.2f} >= {BUMP_1}: +1")

    if kind_ans["confidence"] < KIND_CONFIDENCE_FLOOR:
        tier += 1
        reasons.append("kind uncertain: +1")

    # Haiku only for read-only, low-risk work
    if tier == _tier("haiku"):
        if answers["edits_code"]["noul"] >= 0.5 and signals["multi_module"] >= 0.5:
            tier += 1
            reasons.append("multi-module edit: no haiku")
        elif signals["risky_domain"] >= 0.5:
            tier += 1
            reasons.append("risky domain: no haiku")

    clamped = _clamp(tier, cfg)
    if clamped != tier:
        reasons.append(f"clamped to [{cfg.min_model}, {cfg.max_model}]")
    return Decision(model=MODELS[clamped], kind=kind, complexity=round(complexity, 3), reasons=reasons)
