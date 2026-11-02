"""A verifiable reward and a hackable one, on a toy rebooking task.

A policy chooses among three ways to finish a rebooking: act through
the gateway once ("act"), say it is done without acting ("claim"), or
act twice to be safe ("double"). The naive grader reads the agent's own
final message. The half verifier checks that a booking exists. The
harness grader reads the booking system: exactly one
new booking, on the asked-for flight, within the $250 fare difference.
REINFORCE on a softmax policy learns whichever the reward pays for.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from common.rand import seeded

ACTIONS = ("act", "claim", "double")
STEP_COST = {"act": 0.10, "claim": 0.02, "double": 0.18}


@dataclass
class Outcome:
    said_done: bool
    bookings: int           # new bookings in the system of record
    in_policy: bool


def episode(action: str, rng) -> Outcome:
    if action == "claim":
        return Outcome(True, 0, True)
    tries = 2 if action == "double" else 1
    n = sum(rng.random() < 0.9 for _ in range(tries))
    return Outcome(True, n, rng.random() < 0.98)


def naive(o: Outcome) -> float:
    return 1.0 if o.said_done else 0.0


def exists(o: Outcome) -> float:
    """A half verifier: is there a booking? It never counts them."""
    return 1.0 if o.bookings >= 1 else 0.0


def harness(o: Outcome) -> float:
    return 1.0 if o.bookings == 1 and o.in_policy else 0.0


def train(grader, episodes: int = 3000, rate: float = 0.05,
          seed: int = 17) -> tuple[dict[str, float], float]:
    """Final policy, and the verified success rate of its last 500."""
    rng = seeded(seed, "adapt", "reward", grader.__name__)
    logits = {a: 0.0 for a in ACTIONS}
    base = 0.0
    tail = []
    for i in range(episodes):
        z = sum(math.exp(v) for v in logits.values())
        p = {a: math.exp(v) / z for a, v in logits.items()}
        a = rng.choices(ACTIONS, weights=[p[x] for x in ACTIONS])[0]
        o = episode(a, rng)
        r = grader(o) - STEP_COST[a]
        base += 0.02 * (r - base)
        for x in ACTIONS:
            g = (1.0 if x == a else 0.0) - p[x]
            logits[x] += rate * (r - base) * g * 10
        if i >= episodes - 500:
            tail.append(harness(o))
    z = sum(math.exp(v) for v in logits.values())
    return ({a: math.exp(v) / z for a, v in logits.items()},
            sum(tail) / len(tail))
