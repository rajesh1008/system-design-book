"""The failure catalog, by plane (Section 1).

Each row names where a failure starts, what kind it is, how Lakeshore
sees it, and the first move. Kinds follow a common chaos taxonomy:
crash (an error or a timeout), omission (nothing, or less than asked),
value (a wrong or malformed answer), plus two an agent adds: a wrong
decision, and an effect whose outcome is unknown.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass


@dataclass(frozen=True)
class Failure:
    plane: str
    mode: str
    kind: str
    seen_by: str
    first_move: str


CATALOG = (
    Failure("action", "model call times out", "crash",
            "loop timer", "retry once, then a smaller model"),
    Failure("action", "model returns malformed tool call", "value",
            "schema check", "re-ask once, then to a person"),
    Failure("action", "model repeats a step", "decision",
            "step budget", "stop the run at the budget"),
    Failure("action", "says done before the effect", "decision",
            "chain states", "status from the chain only"),
    Failure("action", "supplier answers after timeout", "unknown",
            "ledger unknown", "replay the key, or look up"),
    Failure("action", "supplier drops the request", "omission",
            "lookup past bound", "retry under the same key"),
    Failure("action", "partial effect, two suppliers", "unknown",
            "verifier per leg", "finish or compensate the leg"),
    Failure("control", "policy engine unreachable", "crash",
            "gateway timer", "no permission, so no effect"),
    Failure("control", "approver queue past its cap", "omission",
            "queue age", "shed to the human queue"),
    Failure("control", "permission reused or stale", "value",
            "key issuer", "refuse; single-use permissions"),
    Failure("knowledge", "fact older than its limit", "value",
            "freshness check", "send the proposal to a person"),
    Failure("knowledge", "source down", "omission",
            "fetch error", "answer only, no proposal"),
    Failure("trail", "decision record not written", "omission",
            "contract C5 test", "block the effect"),
    Failure("trail", "verifier late or missing", "omission",
            "unverified age", "hold 'done'; page the owner"),
    Failure("trail", "settlement disagrees", "value",
            "reconciler", "stop the path, then count"),
    Failure("outside", "effect path outside gateway", "unknown",
            "credential list", "revoke; tool refuses"),
)


def by_plane() -> Counter:
    return Counter(f.plane for f in CATALOG)


def kinds() -> Counter:
    return Counter(f.kind for f in CATALOG)
