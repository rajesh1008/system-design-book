"""Five service objectives for a system that acts, and the one it had.

Each objective names what it counts, the target, the window, the
source of its records, and the owner who answers for it. An objective
with a budget is a ratio of good events to eligible events; the
budget is the bad events the target allows in the window. The
unauthorized-actions objective has no budget: its target is zero
and one event spends it.

A source that did not deliver makes the reading "unknown", never
"met". A missing metric is not a zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .records import Records, Task


@dataclass(frozen=True)
class Objective:
    key: str
    name: str
    counts: str
    target: float            # ratio of good to eligible, or 0 for zero
    window_days: int
    source: str
    owner: str
    slice_by: str = ""       # "kind": a budget per kind of change

    @property
    def budget_ratio(self) -> float:
        return 1.0 - self.target if self.target else 0.0


UPTIME = Objective(
    "uptime", "Front-door availability",
    "requests answered without a 5xx", 0.999, 28, "front_door",
    "Ben Carter")

FIVE = (
    Objective("verified", "Verified outcomes",
              "agent tasks the reconciler verified", 0.99, 28,
              "reconciler", "Marcus Bell", slice_by="kind"),
    Objective("unauthorized", "Unauthorized actions",
              "effects with no permission that matches", 0.0, 28,
              "gateway", "Owen Fletcher"),
    Objective("latency", "Task latency",
              "tasks ended within 40 s (p95 of 40 s)", 0.95, 7,
              "traces", "Marcus Bell"),
    Objective("cost", "Cost per verified outcome",
              "days at or under the band's top", 0.90, 28,
              "provider", "Daniel Price"),
    Objective("backlog", "Escalation backlog",
              "escalations picked up within 60 minutes", 0.98, 7,
              "desk", "Marcus Bell"),
)
BY_KEY = {o.key: o for o in FIVE + (UPTIME,)}
LATENCY_S = 40.0
PICKUP = timedelta(minutes=60)


@dataclass
class Reading:
    key: str
    good: int
    total: int
    budget: float            # bad events the target allows
    bad: int
    status: str              # met, burning, spent, unknown
    note: str = ""

    @property
    def rate(self) -> float | None:
        return self.good / self.total if self.total else None

    @property
    def used(self) -> float | None:
        """Share of the window's budget spent; None if no budget."""
        if self.budget <= 0:
            return None
        return self.bad / self.budget


def _status(bad: int, budget: float, zero: bool = False) -> str:
    if zero:
        return "spent" if bad else "met"
    if bad > budget:
        return "spent"
    return "burning" if bad > 0.5 * budget else "met"


def eligible(tasks: list[Task], start: datetime, end: datetime,
             kind: str = "") -> list[Task]:
    return [t for t in tasks if start <= t.ended < end
            and (not kind or t.kind == kind)]


def read(obj: Objective, rec: Records, start: datetime, end: datetime,
         kind: str = "", band_top: float = 1.76,
         full_window: int | None = None) -> Reading:
    """Read one objective over [start, end). The budget is scaled to
    the share of the objective's window that [start, end) covers, so
    a day's reading spends a day's budget. `full_window` overrides the
    eligible count the budget is figured on."""
    if obj.source in rec.missing:
        return Reading(obj.key, 0, 0, 0.0, 0, "unknown",
                       f"no records from {obj.source}")
    ts = eligible(rec.tasks, start, end, kind)
    if obj.key == "uptime":
        total = sum(t.requests for t in ts)
        bad = sum(t.errors for t in ts)
    elif obj.key == "verified":
        done = [t for t in ts if t.verified is not None]
        total, bad = len(done), sum(not t.verified for t in done)
    elif obj.key == "unauthorized":
        total = len(ts)
        bad = sum(t.unauthorized for t in ts)
        if not total:
            return Reading(obj.key, 0, 0, 0.0, 0, "unknown",
                           "no eligible records")
        return Reading(obj.key, total - bad, total, 0.0, bad,
                       _status(bad, 0, zero=True))
    elif obj.key == "latency":
        total = len(ts)
        bad = sum(t.seconds > LATENCY_S for t in ts)
    elif obj.key == "cost":
        days = {}
        for t in ts:
            d = days.setdefault(t.ended.date(), [0.0, 0])
            d[0] += t.cost_usd
            d[1] += bool(t.verified)
        for u in rec.usage:
            if start <= u.minute < end and u.key != "agent:servicing":
                d = days.setdefault(u.minute.date(), [0.0, 0])
                d[0] += u.input_tokens * UNATTENDED_USD_PER_TOKEN
        total = len(days)
        bad = sum(1 for c, n in days.values()
                  if n == 0 or c / n > band_top)
    elif obj.key == "backlog":
        es = [e for e in rec.escalations if start <= e.queued < end]
        total = len(es)
        bad = sum(1 for e in es if e.picked is None
                  or e.picked - e.queued > PICKUP)
    else:
        raise KeyError(obj.key)
    if not total:
        return Reading(obj.key, 0, 0, 0.0, 0, "unknown",
                       "no eligible records")
    n = full_window if full_window is not None else total
    budget = obj.budget_ratio * n
    return Reading(obj.key, total - bad, total, budget, bad,
                   _status(bad, budget))


# Unattended loops are priced from the provider's export: a small-model
# input token, list price, the only cost the export carries per key.
UNATTENDED_USD_PER_TOKEN = 1.0 / 1_000_000


def read_all(objs, rec: Records, start: datetime, end: datetime,
             kinds: tuple = ()) -> list[Reading]:
    out = []
    for o in objs:
        if o.slice_by == "kind" and kinds:
            for k in kinds:
                r = read(o, rec, start, end, kind=k)
                r.key = f"{o.key}:{k}"
                out.append(r)
        else:
            out.append(read(o, rec, start, end))
    return out
