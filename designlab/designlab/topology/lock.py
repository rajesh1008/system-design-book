"""The talking stick across workers (Section 6).

Chapter 8 gave each itinerary a single writer: a lease with a fencing
token, the talking stick, and a gateway that refuses a lower token.
This module reuses the effect ledger's lease (effects.ledger) for the
stick and asks what happens when one task has two workers.

Two leg workers handle one disrupted itinerary. In some runs both
decide the passenger needs a new connection. A conflicting effect is
two rebookings applied to one passenger, the second made from a read
the first had already made stale.

modes
  none     the gateway applies every command
  shared   the June 16 staging design: the orchestrator takes the
           stick and passes its token to both workers; the gateway
           checks the token, so both commands pass
  stick    each worker takes the stick in its own name before it
           reads for an effect and hands it back after; the gateway
           checks the caller against the holder and the token
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded
from effects.keys import EffectKey
from effects.ledger import Ledger, StaleLease

TTL = 30.0          # seconds a stick is held before it lapses
OVERLAP = 0.30      # runs in which both workers want to rebook
PAUSE_SHARE = 0.01  # holder pauses past its lease (an approval wait)
PAUSE = 45.0


class Stick:
    """One stick per itinerary, kept in the effect ledger's lease."""

    def __init__(self) -> None:
        self.ledger = Ledger()

    def _entry(self, key: str, now: float):
        if key not in self.ledger.entries:
            ek = EffectKey(key, "stick", "talking-stick", key, now)
            self.ledger.reserve(ek, now)
        return self.ledger.entries[key]

    def acquire(self, key: str, holder: str, now: float,
                ttl: float = TTL) -> int:
        self._entry(key, now)
        return self.ledger.acquire(key, holder, now, ttl)

    def holder(self, key: str, now: float) -> str | None:
        e = self._entry(key, now)
        return e.lease_holder if now < e.lease_until else None

    def free_at(self, key: str, now: float) -> float:
        e = self._entry(key, now)
        return e.lease_until if e.lease_holder else now

    def release(self, key: str, holder: str, now: float) -> None:
        e = self._entry(key, now)
        if e.lease_holder == holder:
            e.lease_until = now

    def check(self, key: str, caller: str, token: int, now: float,
              by_caller: bool = True) -> None:
        """The gateway's check. by_caller=False is the June 16 check:
        the token alone, so anyone presenting it passes."""
        e = self._entry(key, now)
        if token != e.lease_token or now >= e.lease_until:
            raise StaleLease(f"{key}: token {token}, current "
                             f"{e.lease_token}")
        if by_caller and e.lease_holder != caller:
            raise StaleLease(f"{key}: held by {e.lease_holder}, "
                             f"command from {caller}")


@dataclass
class LockResult:
    mode: str
    runs: int = 0
    overlaps: int = 0
    conflicts: int = 0
    waited: int = 0          # a worker found the stick held and waited
    stood_down: int = 0      # re-read after the wait: nothing to do
    late_refused: int = 0    # a paused holder's write refused
    extra_seconds: float = 0.0


def run_one(i: int, mode: str, rng, stick: Stick, res: LockResult) -> None:
    key = f"LTG-{5600000 + i}"
    both = rng.random() < OVERLAP
    res.overlaps += both
    workers = ["leg-1", "leg-2"] if both else ["leg-1"]
    starts = {w: rng.uniform(0, 3) for w in workers}
    think = {w: rng.uniform(2, 12) for w in workers}
    paused = rng.random() < PAUSE_SHARE
    rebooked_at: list[float] = []
    if mode in ("none", "shared"):
        token = stick.acquire(key, "lead", 0.0, ttl=120.0) \
            if mode == "shared" else 0
        for w in workers:
            read, commit = starts[w], starts[w] + think[w]
            if any(t <= read for t in rebooked_at):
                continue
            if mode == "shared":
                stick.check(key, w, token, commit, by_caller=False)
            rebooked_at.append(commit)
        if len(rebooked_at) > 1:
            res.conflicts += 1
        return
    order = sorted(workers, key=lambda w: starts[w])
    first, second = order[0], order[-1]
    t1 = stick.acquire(key, first, starts[first])
    commit1 = starts[first] + think[first] + (PAUSE if paused else 0)
    applied = []
    if not paused:
        stick.check(key, first, t1, commit1)
        applied.append(first)
        stick.release(key, first, commit1)
    if second == first:
        if paused:      # lease lapsed; refused, then taken again
            try:
                stick.check(key, first, t1, commit1)
            except StaleLease:
                res.late_refused += 1
            t1 = stick.acquire(key, first, commit1)
            stick.check(key, first, t1, commit1 + 1.0)
            applied.append(first)
        _settle(res, applied)
        return
    t = starts[second]
    try:
        t2 = stick.acquire(key, second, t)
    except StaleLease:
        res.waited += 1
        t = stick.free_at(key, t)
        res.extra_seconds += t - starts[second]
        t2 = stick.acquire(key, second, t)
    if applied:
        res.stood_down += 1          # re-read shows the new connection
        stick.release(key, second, t)
    else:
        commit2 = t + think[second]
        stick.check(key, second, t2, commit2)
        applied.append(second)
        stick.release(key, second, commit2)
    if paused:
        try:
            stick.check(key, first, t1, commit1)
            applied.append(first)
        except StaleLease:
            res.late_refused += 1
    _settle(res, applied)


def _settle(res: LockResult, applied: list[str]) -> None:
    if len(applied) > 1:
        res.conflicts += 1


def trial(mode: str, runs: int = 5_000, seed: int = 27) -> LockResult:
    stick = Stick()
    res = LockResult(mode)
    for i in range(runs):
        res.runs += 1     # same scenario for run i in every mode
        run_one(i, mode, seeded(seed, "lock", str(i)), stick, res)
    return res
