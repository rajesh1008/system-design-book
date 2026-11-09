"""The operating rhythm (section 6) and the cost of a stalled rule.

Each forum has one owner, a cadence, and the decisions it reviews.
The rhythm check fails a decision that no forum reviews: a decision
with an owner but no forum is reviewed only when something breaks.
Times are Chicago (CDT). Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .rights import SIGNED


@dataclass(frozen=True)
class Forum:
    name: str
    cadence: str
    when: str
    owner: str
    minutes: int
    reviews: tuple


FORUMS: tuple[Forum, ...] = (
    Forum("on-call handover", "weekly", "Mon 9:30", "Ben Carter", 30,
          ("stop", "restore", "release")),
    Forum("platform review", "weekly", "Mon 11:00", "Daniel Price",
          60, ("tool.register", "usecase.accept", "budget.loop")),
    Forum("access review", "weekly", "Tue 2:00", "Owen Fletcher", 45,
          ("tool.scopes", "usecase.threat")),
    Forum("gate review", "weekly", "Wed 10:00", "Hannah Clarke", 45,
          ("gate",)),
    Forum("rules review", "weekly", "Thu 9:00", "Marcus Bell", 45,
          ("rules.ops", "autonomy", "message", "bundle.activate")),
    Forum("kill-switch drill", "weekly", "Thu 3:00", "Ben Carter", 30,
          ("stop",)),
    Forum("bill review", "monthly", "1st Mon", "Priya Natarajan", 60,
          ("budget.loop", "budget.envelope")),
    Forum("risk review", "monthly", "2nd Wed", "Rachel Morgan", 60,
          ("rules.refund", "rules.security", "usecase.tier")),
    Forum("card day", "monthly", "last workday", "Daniel Price", 90,
          ("usecase.live",)),
)


def unreviewed(forums=FORUMS, matrix=SIGNED) -> list[str]:
    seen = {k for f in forums for k in f.reviews}
    return [d.key for d in matrix if d.key not in seen]


def weekly_hours(forums=FORUMS) -> float:
    """Meeting hours a week, monthly forums spread over 4.33 weeks."""
    mins = sum(f.minutes if f.cadence == "weekly" else f.minutes / 4.33
               for f in forums)
    return mins / 60


# rebook-v3 (section 5). Rebookings a day with a fare difference over
# $250 and up to $400, same carrier: the work the agent would have
# taken. Weekdays and weekends differ. Illustrative.
WEEKDAY, WEEKEND = 121, 98
AGENT_COST, ASSISTED_COST = 1.61, 6.20
COULD = date(2026, 8, 7)    # active, had an owner signed on Aug 5
DID = date(2026, 8, 17)     # active after the Aug 13 ruling


def stalled(start: date = COULD, end: date = DID) -> list[tuple]:
    out, d = [], start
    while d < end:
        out.append((d, WEEKEND if d.weekday() >= 5 else WEEKDAY))
        d += timedelta(days=1)
    return out


def stall_cost(days=None) -> tuple[int, int, float]:
    days = days if days is not None else stalled()
    n = sum(c for _, c in days)
    return len(days), n, n * (ASSISTED_COST - AGENT_COST)
