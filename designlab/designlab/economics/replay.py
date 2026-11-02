"""The weekend of July 25 and 26, replayed in dollars.

Chapter 37's simulation gives the loop's billed calls minute by
minute. Each one goes through a Gateway under a policy; a call the
gateway lets through is billed by the provider at the storm's price
whatever the gateway counted, and a refused call is never sent. The
fare watch runs alongside, one run a minute, so an envelope that the
storm empties shows what else it stops.

The replay keeps the loop as it was in July, max_tokens 32,000 and
retries in three layers. A policy is tested against the failure that
happened, not against the loop after its fixes, because the next
storm will come from a defect nobody has found yet.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from reliability import storm as rs

from . import bill
from .policy import DR38, Gateway, Refused, SpendPolicy

FARE_RUN_USD = 1.85 / 1440        # a fare-watch run, one a minute
FARE_RUN_WORST = 2 * FARE_RUN_USD
LOOP_SHARE = 0.20                 # loops' share of the rate limit


@dataclass
class Result:
    policy: str
    billed: float          # the waiver watch, as the provider bills
    fare_billed: float
    counted: float
    calls: int
    refused: int
    fare_refused: int
    servicing_429_min: int
    events: list
    path: list             # (minute, waiver watch billed so far)


@lru_cache(maxsize=None)
def run(policy: SpendPolicy = DR38) -> Result:
    st = bill.weekend()
    gw = Gateway(policy)
    worst = bill.storm_call().usd("small")
    billed = fare = 0.0
    calls = refused = fare_refused = n = over_min = 0
    path = []
    for i, m in enumerate(st.minutes):
        sent = 0
        for _ in range(m.loop_billed):
            n += 1
            try:
                billed += gw.call("waiver-watch", f"r{n // 9}", m.t,
                                  worst, None)
                calls += 1
                sent += 1
            except Refused:
                refused += 1
        try:
            fare += gw.call("fare-watch", f"f{i}", m.t,
                            FARE_RUN_WORST, FARE_RUN_USD)
        except Refused:
            fare_refused += 1
        sched = rs.SAT if m.t.day == 25 else rs.SUN
        want = sched[m.t.hour] * rs.SERVICE_TOKENS + \
            sent * rs.LOOP_TOKENS
        over_min += want > rs.LIMIT
        path.append((m.t, billed))
    counted = gw.spent_by("waiver-watch")
    return Result(policy.name, billed, fare, counted, calls, refused,
                  fare_refused, over_min, gw.events, path)


def rate_share_only() -> tuple[float, int]:
    """No spend policy, only a per-identity share of the rate limit:
    the loop may send at most 20% of the shared tokens a minute.
    Returns the bill and the servicing minutes over the limit."""
    cap = int(LOOP_SHARE * rs.LIMIT / rs.LOOP_TOKENS)
    calls = over = 0
    for m in bill.weekend().minutes:
        sent = min(m.loop_billed, cap)
        calls += sent
        sched = rs.SAT if m.t.day == 25 else rs.SUN
        over += (sched[m.t.hour] * rs.SERVICE_TOKENS
                 + sent * rs.LOOP_TOKENS) > rs.LIMIT
    return calls * bill.storm_call().usd("small"), over
