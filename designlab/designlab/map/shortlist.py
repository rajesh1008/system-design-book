"""Score the map against the five gaps and pick the bake-off shortlist.

score = gap points - lock-in weight x (lock_in - 1) / 2

Gap points: closes 2, partial 1, claims 0, none 0, over G1 to G5.
Lock-in runs 1 to 5, so at weight 1 the penalty runs 0 to 2.
Runtimes must be generally available and at least partial on G2 (a
runtime with no place for a permission decision is a sandbox, not a
runtime Lakeshore can put money behind). Frameworks must be generally
available at 1.0 or later. Ties break on lower lock-in, then name.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import GAP_POINTS, Map, Option

RULES = {
    "runtime": {"take": 3, "status": ("ga",), "g2_min": 1},
    "framework": {"take": 2, "status": ("ga",), "g2_min": 1},
}


@dataclass
class Scored:
    option: Option
    score: float
    reason: str = ""

    @property
    def eligible(self) -> bool:
        return not self.reason


def score(opt: Option, lockin_weight: float = 1.0) -> float:
    return opt.points - lockin_weight * (opt.lock_in - 1) / 2


def rank(m: Map, category: str, lockin_weight: float = 1.0) -> list:
    rule = RULES[category]
    out = []
    for o in m.by_category().get(category, []):
        reason = ""
        if o.status not in rule["status"]:
            reason = f"status {o.status}"
        elif GAP_POINTS[o.gaps["G2"]] < rule["g2_min"]:
            reason = "no permission hook (G2)"
        out.append(Scored(o, score(o, lockin_weight), reason))
    out.sort(key=lambda s: (not s.eligible, -s.score,
                            s.option.lock_in, s.option.name))
    return out


def shortlist(m: Map, lockin_weight: float = 1.0) -> dict:
    return {cat: [s for s in rank(m, cat, lockin_weight)
                  if s.eligible][: rule["take"]]
            for cat, rule in RULES.items()}


def recheck(m: Map, picks: dict) -> list:
    """Shortlisted options whose newest claim is past the stale window."""
    stale = {w.split(":")[0] for w in m.warnings if "days old" in w}
    return [s.option.id for group in picks.values() for s in group
            if s.option.id in stale]
