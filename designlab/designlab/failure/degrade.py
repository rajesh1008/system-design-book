"""Degraded modes, a ladder (Section 4).

Each rung keeps what is still safe and stops what is not:

    full           propose, permit, act, verify
    propose-only   propose and permit; effects held with their keys
    answer-only    answer from fresh facts; no proposals
    people-only    the agent is off; every contact to a person

The rung is computed, never chosen by the model. Kill switch tiers:
1 holds one tool's effects, 2 holds every effect at the gateway, 3
turns the agent off.
"""
from __future__ import annotations

from dataclasses import dataclass, field

LADDER = ("full", "propose-only", "answer-only", "people-only")


def rung(breaker_open: bool = False, kill_tier: int = 0,
         control_down: bool = False, knowledge_stale: bool = False) -> str:
    if kill_tier >= 3:
        return "people-only"
    if control_down or knowledge_stale:
        return "answer-only"
    if breaker_open or kill_tier in (1, 2):
        return "propose-only"
    return "full"


@dataclass
class HoldQueue:
    """Effects held while their provider's breaker is open. Each item
    keeps its permission and key, so a release is the same effect."""
    items: list[tuple[float, object]] = field(default_factory=list)
    waits: list[float] = field(default_factory=list)

    def hold(self, now: float, item: object) -> None:
        self.items.append((now, item))

    def release(self, now: float, per_s: float) -> list[tuple[float, object]]:
        """Release everything held, paced at `per_s`. Returns (time,
        item) pairs at which each held effect is attempted."""
        out, t = [], now
        for held_at, item in self.items:
            out.append((t, item))
            self.waits.append(t - held_at)
            t += 1.0 / per_s
        self.items = []
        return out
