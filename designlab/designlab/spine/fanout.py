"""Fan-out: one airline cancellation, about 3,900 itineraries, three
queues.

The cancellation is an event: a fact the airline published. The
fan-out turns it into one command per itinerary, keyed by itinerary,
with an id derived from the event id, so a redelivered event yields
the same commands and the inbox absorbs them. Each command's planner
routes the result to one of three queues:

  work       rebook inside rebook-v2 (same carrier, fare difference
             within $250): act and notify, no person
  approvals  refund under refunds-v3: act with approval
  refusals   outside both: the agent desk, with a promise time

All amounts are illustrative and in US dollars.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from common.rand import seeded

from .inbox import Inbox

QUEUES = ("work", "approvals", "refusals")
REBOOK_LIMIT = 250.00


@dataclass(frozen=True)
class Command:
    msg_id: str
    key: str
    queue: str
    at_s: float          # seconds after the event when it was routed


def itineraries(seed: int, n: int = 3_900) -> list[dict]:
    """The affected itineraries, seeded. option: hours to the first
    same-carrier seat, or None; diff: its fare difference."""
    rng = seeded(seed, "fanout", "itineraries")
    rows = []
    for i in range(n):
        r = rng.random()
        if r < 0.0980:
            opt, diff = None, 0.0               # nothing within 24 h
        else:
            opt = rng.choice((2, 3, 5, 8, 14, 20))
            diff = round(rng.expovariate(1 / 70), 2)
        rows.append({"key": f"LTG-{4800000 + i}", "option_h": opt,
                     "diff": diff})
    return rows


def route(row: dict) -> str:
    if row["option_h"] is None:
        return "approvals"
    if row["diff"] <= REBOOK_LIMIT:
        return "work"
    return "refusals"


def fan_out(event_id: str, rows: list[dict], refund_rate: float = 400,
            search_rate: float = 20) -> list[Command]:
    """Route every itinerary. Refund proposals are built by rule (an
    airline cancellation makes the unused fare refundable), at up to
    refund_rate a minute; rebooking needs a supplier seat search, at
    search_rate a second. Times model when each command is routed."""
    out = []
    n_ref = n_srch = 0
    for row in rows:
        q = route(row)
        if q == "approvals":
            at = n_ref * 60 / refund_rate
            n_ref += 1
        else:
            at = n_srch / search_rate
            n_srch += 1
        out.append(Command(f"{event_id}:{row['key']}", row["key"], q,
                           round(at, 2)))
    return out


def deliver(cmds: list[Command], inbox: Inbox) -> Counter:
    c: Counter = Counter()
    for m in cmds:
        c[inbox.handle(m.msg_id, m.key, 1, m.queue)] += 1
    return c


def summary(cmds: list[Command]) -> dict:
    per = Counter(c.queue for c in cmds)
    first_min = Counter(c.queue for c in cmds if c.at_s < 60)
    last = {q: max((c.at_s for c in cmds if c.queue == q), default=0)
            for q in QUEUES}
    return {"total": len(cmds), "per": per, "first_min": first_min,
            "last_s": last}
