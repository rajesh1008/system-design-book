"""Burn-rate alerts read from the records, two windows per rule.

Burn rate is the bad share in a window divided by the share the
budget allows: at 1.0 the budget lasts exactly its window, at 10 a
28-day budget is gone in under three days. A rule pages when a long
window and a short window both burn past its threshold; the long
window says the burn is real, the short one says it is still
happening. A page also needs a few bad events, because a 5-minute
window at three in the morning holds one task.

Lakeshore's rules (DR-37.1):
  page    1 hour and 5 minutes, both at 10x or more, 3 bad in the hour
  ticket  6 hours and 30 minutes, both at 3x or more, 3 bad
  zero    any unauthorized action pages at once
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta

from .objectives import LATENCY_S, Objective
from .records import Task


@dataclass(frozen=True)
class Rule:
    name: str
    long: timedelta
    short: timedelta
    factor: float
    min_bad: int = 0


PAGE = Rule("page", timedelta(hours=1), timedelta(minutes=5), 10.0, 3)
TICKET = Rule("ticket", timedelta(hours=6), timedelta(minutes=30), 3.0, 3)
RULES = (PAGE, TICKET)


def events(obj: Objective, tasks: list[Task], kind: str = ""):
    """(time, bad) per eligible task, at the moment its record lands."""
    out = []
    for t in tasks:
        if kind and t.kind != kind:
            continue
        if obj.key == "verified":
            if t.verified is None or t.reconciled is None:
                continue
            out.append((t.reconciled, not t.verified))
        elif obj.key == "latency":
            out.append((t.ended, t.seconds > LATENCY_S))
        elif obj.key == "uptime":
            out.append((t.ended, t.errors > 0))
        elif obj.key == "unauthorized":
            out.append((t.ended, t.unauthorized > 0))
    out.sort()
    return out


class Series:
    """Events sorted by time, with running counts for fast windows."""

    def __init__(self, evs):
        self.times = [t for t, _ in evs]
        self.cum = [0]
        for _, b in evs:
            self.cum.append(self.cum[-1] + bool(b))

    def window(self, end: datetime, span: timedelta) -> tuple[int, int]:
        lo = bisect_right(self.times, end - span)
        hi = bisect_right(self.times, end)
        return self.cum[hi] - self.cum[lo], hi - lo


def rate(evs, end: datetime, span: timedelta, budget_ratio: float):
    s = evs if isinstance(evs, Series) else Series(evs)
    bad, n = s.window(end, span)
    if not n or budget_ratio <= 0:
        return 0.0, bad, n
    return (bad / n) / budget_ratio, bad, n


@dataclass
class Alert:
    objective: str
    rule: str
    at: datetime
    long_burn: float
    short_burn: float
    bad_in_long: int


def scan(obj: Objective, tasks: list[Task], start: datetime,
         end: datetime, kind: str = "", rules=RULES,
         step: timedelta = timedelta(minutes=1)) -> list[Alert]:
    """The first firing of each rule, minute by minute."""
    evs = events(obj, tasks, kind)
    name = f"{obj.key}:{kind}" if kind else obj.key
    if obj.key == "unauthorized":
        hits = [t for t, b in evs if b and start <= t < end]
        return [Alert(name, "zero", hits[0], 0, 0, 1)] if hits else []
    evs = Series(evs)
    fired, out = set(), []
    t = start
    while t < end:
        for r in rules:
            if r.name in fired:
                continue
            lb, bad, _ = rate(evs, t, r.long, obj.budget_ratio)
            sb, _, _ = rate(evs, t, r.short, obj.budget_ratio)
            if lb >= r.factor and sb >= r.factor and bad >= r.min_bad:
                fired.add(r.name)
                out.append(Alert(name, r.name, t, lb, sb, bad))
        t += step
    return out
