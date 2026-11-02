"""Cost per verified outcome, the way finance closes a month.

The drivers are Chapter 18's seven lines for the month as it ran
(`cost.forecast.planned` with the month's real autonomy split and
hand-off rate). On top of them sit the two things July had that the
forecast did not: the spend no task caused, and an incident's rework.

Finance's rule from May 6 put spend with no task id into a shared
pool split across the agent and assisted paths by their share of
changes. Loops have no task id, so the storm landed in the pool and
46.7% of it landed on the agent path's outcomes. DR-38.1 changes the
rule: spend is charged by identity, and a loop's spend, storms
included, goes to the loop's owner. Ordinary retries of a task stay
in that task's cost, because the task caused them.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from cost.forecast import planned
from cost.unit import LOADED_PER_MIN, by_kind, month_cost

from . import bill

# (agent, assisted, hand-off rate) as each month ran
AS_RUN = {"July": (0.14, 0.16, 0.13), "August": (0.36, 0.23, 0.11)}
BAND = {"July": (1.59, 1.68, 1.76), "August": (1.58, 1.66, 1.75)}

# INC-5, July 8: 44 rebookings reissued on the old flight number for
# 40 travelers; the desk redid each one and credited each traveler.
INC5_REBOOKINGS, INC5_TRAVELERS = 44, 40
INC5_DESK_MIN, INC5_CREDIT, INC5_FEE = 24.0, 12.00, 0.40


@lru_cache(maxsize=None)
def drivers(month: str) -> dict:
    agent, assisted, handoff = AS_RUN[month]
    return month_cost(planned(f"{month} 2026", agent, assisted,
                              handoff=handoff))


def inc5_rework() -> float:
    return (INC5_REBOOKINGS * INC5_DESK_MIN * LOADED_PER_MIN
            + INC5_TRAVELERS * INC5_CREDIT
            + INC5_REBOOKINGS * INC5_FEE)


def agent_share(month: str) -> float:
    agent, assisted, _h = AS_RUN[month]
    return agent / (agent + assisted)


@dataclass(frozen=True)
class Close:
    month: str
    verified: int
    drivers: float        # Chapter 18's seven lines, per outcome
    pooled: float         # task-less incident spend, per outcome
    rework: float         # incident rework, per outcome
    total: float


def close(month: str, rule: str = "pool") -> Close:
    """`rule="pool"` is finance's May rule; `"identity"` is DR-38.1."""
    d = drivers(month)
    v = d["verified"]
    pooled = rework = 0.0
    if month == "July":
        if rule == "pool":
            pooled = bill.storm_usd() * agent_share(month) / v
        rework = inc5_rework() / v
    per = d["per_outcome"]
    return Close(month, v, per, pooled, rework, per + pooled + rework)


def kinds(month: str, rule: str = "pool") -> dict[str, float]:
    """Per kind of change. Pooled spend is split by changes, so every
    kind carries the same share; INC-5's rework is rebooking's own."""
    agent, assisted, handoff = AS_RUN[month]
    k = by_kind(planned(f"{month} 2026", agent, assisted,
                        handoff=handoff))
    c = close(month, rule)
    out = {}
    for name, row in k.items():
        extra = c.pooled
        if name == "rebook" and c.rework:
            extra += inc5_rework() / row["verified"]
        out[name] = row["per_outcome"] + extra
    return out


# Monday-to-Sunday weeks around the storm; days in each week in July.
WEEKS = (("Jun 29-Jul 5", 5), ("Jul 6-12", 7), ("Jul 13-19", 7),
         ("Jul 20-26", 7), ("Jul 27-Aug 2", 5))


def weekly() -> list[tuple[str, float, float]]:
    """The two numbers a weekly report can lead with: what a million
    tokens cost, and what a verified outcome cost."""
    d = drivers("July")
    per_day_v = d["verified"] / 31
    runs_day = bill.SERVICE_RUNS["July"] / 31
    rows = []
    for name, days in WEEKS:
        usd = runs_day * days * bill.SERVICE_RUN_USD
        tok = runs_day * days * bill.SERVICE_RUN_TOKENS
        extra = 0.0
        if name == "Jul 20-26":
            s = bill.invoice("July")[3]
            usd, tok = usd + s.usd, tok + s.tokens
            extra += bill.storm_usd() * agent_share("July")
        if name == "Jul 6-12":
            extra += inc5_rework()
        v = per_day_v * days
        rows.append((name, usd / tok * 1e6,
                     d["per_outcome"] + extra / v))
    return rows
