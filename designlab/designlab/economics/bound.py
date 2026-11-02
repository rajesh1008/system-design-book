"""The worst case before the first call.

A loop's spend can be bounded before it runs: the tree of calls a run
can make, times each call's worst case (input cap plus max_tokens),
times the attempts every layer may add, times the runs a trigger can
start. If any factor has no cap, the bound is infinite, and the only
bound left is the one the gateway enforces at run time.

July's waiver watch had two unbounded factors: a re-queue with no cap
and max_tokens set for the longest notice ever filed. August's loop
(INC-6's fixes, due August 7) has retries in one layer, a timeout
that fails the step, and an extraction max_tokens of 4,096.
"""
from __future__ import annotations

from dataclasses import dataclass

from serving.prices import Bill

INPUT_CAP = 8_000                 # the notice, truncated


@dataclass(frozen=True)
class Step:
    name: str
    role: str
    tokens_in: int
    max_tokens: int

    def worst(self) -> float:
        return Bill(uncached=self.tokens_in,
                    output=self.max_tokens).usd(self.role)


@dataclass(frozen=True)
class Config:
    name: str
    steps: tuple
    attempts: int                 # product over every retrying layer
    requeues: int | None          # None: no cap


JULY = Config("July", (Step("extract", "small", INPUT_CAP, 32_000),
                       Step("map", "mid", 14_000, 1_024)),
              attempts=3 * 3, requeues=None)
AUGUST = Config("August", (Step("extract", "small", INPUT_CAP, 4_096),
                           Step("map", "mid", 14_000, 1_024)),
                attempts=3, requeues=0)


def per_run(c: Config) -> float:
    return c.attempts * sum(s.worst() for s in c.steps)


def per_trigger(c: Config) -> float | None:
    """Worst spend one notice can start; None means unbounded."""
    if c.requeues is None:
        return None
    return per_run(c) * (1 + c.requeues)
