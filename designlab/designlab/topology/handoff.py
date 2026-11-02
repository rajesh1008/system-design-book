"""The relay baton: a handoff is offered, accepted, or unknown (Section 3).

A handoff moves a case, and with it the stick, from one owner to
another. The lead offers it; the receiver accepts by taking the stick
in its own name. If the acceptance does not come back, the handoff is
unknown, and unknown is resolved by reading who holds the stick, not
by guessing. Three designs over the same 1,000 handoffs:

  fire-and-forget  the lead marks the case handed off when it sends
  ack-and-retry    the lead waits for an acknowledgment and re-offers
                   to another worker when none comes back
  baton            acceptance is taking the stick; a missing
                   acknowledgment is unknown until the stick is read
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded

from .lock import Stick

ACK_LOST = 0.03       # the receiver accepted; the reply did not arrive
RECEIVER_DIED = 0.01  # the receiver failed before it accepted


@dataclass
class HandoffResult:
    design: str
    handoffs: int = 0
    orphaned: int = 0      # no owner: the case sits until a person asks
    two_owners: int = 0    # two workers each think the case is theirs
    unknown: int = 0       # resolved by reading the stick
    reoffered: int = 0


def trial(design: str, n: int = 1_000, seed: int = 27) -> HandoffResult:
    res = HandoffResult(design)
    stick = Stick()
    for i in range(n):
        rng = seeded(seed, "handoff", str(i))
        key = f"LTG-{5700000 + i}"
        res.handoffs += 1
        died = rng.random() < RECEIVER_DIED
        lost = (not died) and rng.random() < ACK_LOST
        now = 0.0
        if not died:
            stick.acquire(key, "worker-a", now)     # accepted
        if design == "fire-and-forget":
            res.orphaned += died
            continue
        if not (died or lost):
            continue                                 # offered, accepted
        if design == "ack-and-retry":
            res.reoffered += 1
            if lost:
                res.two_owners += 1                  # a and b both work
            continue
        # baton: unknown until the stick says who holds it
        res.unknown += 1
        holder = stick.holder(key, now + 1.0)
        if holder is None:                           # nobody: re-offer
            res.reoffered += 1
            stick.acquire(key, "worker-b", now + 1.0)
    return res
