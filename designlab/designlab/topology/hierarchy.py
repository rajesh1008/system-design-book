"""Hierarchies: what a fact survives on its way down (Section 4).

A case carries eight facts the final effect depends on (the traveler,
the itinerary, the leg, the fare-difference limit, the refund limit,
the customer's stated constraint, the approval, the deadline). Each
level of a hierarchy rewrites the brief for the level below. A free
summary keeps each fact with probability KEEP; a pinned fact list is
copied verbatim and keeps it unless the list itself is dropped, which
the level's check catches. Every level also adds one call down and
one call up to the critical path.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded

FACTS = 8
KEEP = 0.985            # a free summary keeps a given fact
PINNED_DROP = 0.001     # a pinned list is dropped and not caught
SECONDS_PER_CALL = 2.2
BRIEF_TOKENS = 1_200


@dataclass
class DepthResult:
    depth: int
    style: str
    cases: int
    intact: int
    seconds_added: float
    brief_tokens: int


def trial(depth: int, style: str, cases: int = 1_200,
          seed: int = 27) -> DepthResult:
    intact = 0
    for i in range(cases):
        rng = seeded(seed, "hier", style, str(depth), str(i))
        ok = True
        for _ in range(depth):
            if style == "free":
                ok &= all(rng.random() < KEEP for _ in range(FACTS))
            else:
                ok &= rng.random() >= PINNED_DROP
        intact += ok
    return DepthResult(depth, style, cases, intact,
                       2 * depth * SECONDS_PER_CALL,
                       depth * BRIEF_TOKENS)
