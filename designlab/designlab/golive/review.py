"""The review on Monday, September 21, 2026: recovery measured, the
fall card, and the three designs that changed.

Recovery is measured on the daily verified-outcome rate, the number
the scoreboard fell on. The storm day's rate comes from the replay;
the days after close the gap to the August level at a rate set by
how fast the reconcilers finished the evening's re-canceled flights
and the held work (a time constant of 1.2 days, from the record).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from common.rand import seeded
from cost.unit import LOADED_PER_MIN

from .replay import Result, run

BASE_VERIFIED = 0.996          # August's rate, the level to return to
GATE = 0.995                   # the year-end card's verified line
TAU_DAYS = 1.2
MONTH_COST_PER_VO = 1.61       # September close
NORMAL_DAY_MODEL_USD = 210.00  # an ordinary September day
MISS_DESK_MIN, MISS_CREDIT, MISS_FEE = 24.0, 12.00, 0.40


def daily_verified(r: Result | None = None, first: int = 7,
                   last: int = 20) -> list[tuple[int, float]]:
    r = r or run("as-run")
    rng = seeded(2026, "golive", "recovery")
    out = []
    for d in range(first, last + 1):
        jitter = (rng.random() - 0.5) * 0.0008
        if d < 10:
            v = BASE_VERIFIED + jitter
        elif d == 10:
            v = r.verified_rate
        else:
            gap = BASE_VERIFIED - r.verified_rate
            v = BASE_VERIFIED - gap * math.exp(-(d - 10) / TAU_DAYS)
            v += jitter * 0.5
        out.append((d, v))
    return out


def recovered_on(series) -> int:
    """First day after the storm back at or above the card's line."""
    for d, v in series:
        if d > 10 and v >= GATE:
            return d
    return -1


def storm_cost_per_vo(r: Result | None = None) -> float:
    r = r or run("as-run")
    extra_model = r.model_usd - NORMAL_DAY_MODEL_USD
    rework = r.missed * (MISS_DESK_MIN * LOADED_PER_MIN + MISS_CREDIT
                         + MISS_FEE)
    vo = r.agent_effects * r.verified_rate
    return MONTH_COST_PER_VO + (extra_model + rework) / vo


@dataclass(frozen=True)
class Design:
    record: str
    owner: str
    signer: str
    change: str
    reverse_if: str


DESIGNS = (
    Design("R-RBK-1", "Marcus Bell", "Marcus Bell",
           "desk queue ordered by departure time; rebookings "
           "leaving within six hours first",
           "missed departures per 1,000 rebooking cards rise"),
    Design("R-RFD-1", "Sarah Whitfield (budget)", "Rachel Morgan",
           "surge rule: involuntary refunds to $500 skip the "
           "approver; Rachel's signature only; 12 h expiry",
           "refund error under the rule passes 0.5%, or the rule "
           "runs past expiry"),
    Design("R-PLT-1", "Ben Carter", "Sarah Whitfield",
           "storm reserve: $2,500 of model budget released on a "
           "declared weather incident; queue alert by urgency",
           "reserve spent on a day that was not declared"),
)


def card_lines(r: Result | None = None) -> list[str]:
    r = r or run("as-run")
    series = daily_verified(r)
    back = recovered_on(series)
    return [
        "Fall card, Thursday, September 10, 2026",
        f"  verified outcomes      {r.verified_rate:.1%} (Aug "
        f"{BASE_VERIFIED:.1%})",
        f"  approval queue peak    {r.peak_depth:,}; cleared in "
        f"{r.hours_to_clear:.0f} h",
        f"  missed departures      {r.missed}",
        f"  cost per VO, the day   ${storm_cost_per_vo(r):.2f} "
        f"(month ${MONTH_COST_PER_VO:.2f})",
        "  duplicates             212 (none new); unauthorized 0",
        "  incidents              7 (INC-7)",
        f"  back to {GATE:.1%}          Sept {back}",
    ]


def design_lines() -> list[str]:
    out = []
    for d in DESIGNS:
        out.append(f"{d.record}  owner {d.owner}; signs {d.signer}")
        words, line = d.change.split(), "  "
        for w in words:
            if len(line) + len(w) + 1 > 68:
                out.append(line.rstrip())
                line = "  "
            line += w + " "
        out.append(line.rstrip())
    return out
