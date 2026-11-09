"""Shadow: the candidate answers recorded traffic with its effects
disabled, and every proposal that differs from production's is read.

Replay (Chapter 35) serves recorded model answers, so it cannot say
what a new model would answer. A shadow calls the candidate's models
on the recorded inputs, live, and stops at the proposal: its effect
tools record the call and refuse it. What it produces is a diff, one
row per run whose proposal differs, and a reviewer's verdict on each.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

DAYS = ("08-10", "08-11", "08-12", "08-13", "08-14", "08-15", "08-16",
        "08-17", "08-18", "08-19", "08-20", "08-21", "08-22", "08-23")
# Rebookings per day, August 10 to 23, 2026.
PER_DAY = (742, 761, 755, 768, 790, 702, 688, 744, 771, 769, 772, 781,
           716, 691)
KINDS = ("same option, other wording", "other option, as good",
         "other option, better for traveler", "other option, worse",
         "hand-off instead of proposal")
WEIGHTS = (0, 108, 141, 47, 24)   # per 10,000 runs, by kind index


def _u(key: str) -> float:
    h = hashlib.sha256(key.encode()).digest()
    return int.from_bytes(h[:8], "big") / 2 ** 64


@dataclass
class EffectTool:
    """A shadow's effect tool: records the call, sends nothing."""
    name: str
    calls: list[str] = field(default_factory=list)

    def __call__(self, run_id: str, **args) -> dict:
        self.calls.append(run_id)
        return {"status": "refused", "why": "shadow: effects disabled"}


@dataclass
class Shadow:
    runs: int = 0
    differ: dict[str, int] = field(default_factory=dict)
    reviewed: int = 0
    rows: list[tuple[str, str]] = field(default_factory=list)
    tool: EffectTool = field(default_factory=lambda:
                             EffectTool("rebook_ticket"))

    @property
    def n_differ(self) -> int:
        return sum(self.differ.values())


def run(candidate: str = "change-intent@1.1 on haiku-5-5#2026-08",
        reviewed: bool = True) -> Shadow:
    """Two weeks of recorded rebooking traffic against the candidate."""
    sh = Shadow()
    cum = []
    acc = 0
    for w in WEIGHTS:
        acc += w
        cum.append(acc / 10_000)
    for day, n in zip(DAYS, PER_DAY):
        for i in range(n):
            rid = f"rb-{day}-{i:04d}"
            sh.runs += 1
            sh.tool(rid, booking="recorded")
            u = _u(candidate + rid)
            for k, edge in enumerate(cum):
                if u < edge:
                    sh.differ[KINDS[k]] = sh.differ.get(KINDS[k], 0) + 1
                    sh.rows.append((rid, KINDS[k]))
                    break
    sh.reviewed = sh.n_differ if reviewed else 0
    return sh
