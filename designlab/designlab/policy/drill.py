"""The weekly kill-switch drill, timed from the decision to stop.

A drill runs against staging under replayed production traffic and
times four facts separately, because a switch that answers 200 has
proven only the first:

  received            the pull is recorded (the switch's own answer)
  no new commands     the last effect the far end saw was forwarded
  in-flight settled   the last effect sent before the stop finished
  safe state          the far end's own counter stayed flat for the
                      quiet window, read by a poller every 5 s

Time to stop is the moment the safe state is observed, minus the
moment someone decided to stop. Tier three adds two more facts: the
harness reports no running case, and a call with the agent's old
token is refused.

The parts are modeled from what the drill measures; the numbers are
the model's, seeded, and Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

REPLICAS = 4
POLL_S = 5.0          # each gateway replica reads the flag every 5 s
VERIFY_POLL_S = 5.0   # the verifier reads the far-end counters
QUIET_S = 20.0        # the far end must stay flat this long
TIMEOUT_S = 8.0       # the processor call timeout
RATE = {1: 0.6, 2: 1.8, 3: 1.8}   # effects per second in the tier's scope


@dataclass
class Report:
    tier: int
    decided: float = 0.0
    received: float | None = None
    no_new: float | None = None
    settled: float | None = None
    runs_stopped: float | None = None
    token_refused: float | None = None
    safe: float | None = None

    @property
    def time_to_stop(self) -> float | None:
        return None if self.safe is None else self.safe - self.decided


def run(tier: int, seed: int, broken: bool = False) -> Report:
    """One drill. `broken` writes the flag to a key no gateway reads."""
    rng = random.Random(seed * 10 + tier)
    rep = Report(tier)
    press = rng.uniform(8.0, 22.0)        # page, open console, confirm
    rep.received = press
    lags = [rng.uniform(0.0, POLL_S) for _ in range(REPLICAS)]
    cutoff = [press + lag if not broken else float("inf")
              for lag in lags]
    horizon = press + 180.0
    t, forwarded = 0.0, []
    while t < horizon:
        t += rng.expovariate(RATE[tier])
        replica = rng.randrange(REPLICAS)
        if t < cutoff[replica]:
            dur = min(rng.lognormvariate(0.2, 0.7), TIMEOUT_S)
            forwarded.append((t, t + dur))
    last_fwd = max(a for a, _ in forwarded)
    last_done = max(b for _, b in forwarded)
    if broken:
        return rep                         # received, nothing else
    rep.no_new = last_fwd
    rep.settled = last_done
    flat_from = max(last_fwd, last_done)
    if tier == 3:
        # cases stop at their next step boundary; a model step that is
        # running finishes and its tool calls are refused
        rep.runs_stopped = press + max(rng.uniform(8.0, 38.0)
                                       for _ in range(6))
        # the identity service revokes the token; the check is a call
        rep.token_refused = press + rng.uniform(15.0, 40.0)
        flat_from = max(flat_from, rep.runs_stopped)
    first = flat_from + QUIET_S
    safe = VERIFY_POLL_S * (int(first // VERIFY_POLL_S) + 1)
    if tier == 3:
        safe = max(safe, rep.token_refused)
    rep.safe = safe
    return rep


def weekly(tier: int, weeks: int = 9, seed: int = 504) -> list[Report]:
    """Nine Thursday drills, April 30 to June 25, at one tier."""
    return [run(tier, seed + w) for w in range(weeks)]


def medians(weeks: int = 9) -> dict[int, float]:
    return {tier: statistics.median(r.time_to_stop
                                    for r in weekly(tier, weeks))
            for tier in (1, 2, 3)}
