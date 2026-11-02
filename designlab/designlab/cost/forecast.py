"""Forecasting the bill from drivers, not from last month's total.

A driver forecast multiplies things someone owns and can check:
changes a month, the planned agent share, attempts per verified
outcome, steps and tokens per attempt, and the price of a step. The
naive forecast multiplies last month's cost per outcome by next
month's outcomes. Both are written down on June 1, 2026, before any
of the months they forecast.
"""
from __future__ import annotations

from dataclasses import replace

from .unit import MAY, Month, month_cost, with_levers

PLATFORM_FIXED = 2_400.0       # run store, trail, eval harness, on-call
PLATFORM_PER_ATTEMPT = 0.295   # gateway and run-store capacity
# Planned shares for the ramp (Chapter 4's plan, as of June 1, 2026).
PLAN = (("June 2026", 0.14, 0.16), ("July 2026", 0.22, 0.18),
        ("August 2026", 0.30, 0.20))
# Scoreboard actuals, filled in as months close.
ACTUAL = {"March 2026": 2.60, "April 2026": 2.95, "May 2026": 1.84,
          "June 2026": 1.79, "July 2026": 2.02}
# The band: steps and tokens per attempt drift 15% either way, and
# hand-offs move two points.
DRIFT = 0.15
HANDOFF_BAND = 0.02


def planned(name: str, agent: float, assisted: float,
            base: Month = MAY, drift: float = 0.0,
            handoff: float | None = None) -> Month:
    m = replace(base, name=name, agent=agent, assisted=assisted,
                handoff=base.handoff if handoff is None else handoff)
    m = with_levers(m, token_scale=1.0 + drift,
                    retry_scale=1.0 + drift)
    executed = round(m.changes * agent / m.verified_rate)
    attempts = round(executed / (1.0 - m.handoff))
    return replace(m, platform=PLATFORM_FIXED
                   + PLATFORM_PER_ATTEMPT * attempts)


def forecast(seed: int = 18) -> list[dict]:
    rows = []
    for name, agent, assisted in PLAN:
        mid = month_cost(planned(name, agent, assisted), seed)
        lo = month_cost(planned(name, agent, assisted, drift=-DRIFT,
                                handoff=MAY.handoff - HANDOFF_BAND),
                        seed)
        hi = month_cost(planned(name, agent, assisted, drift=DRIFT,
                                handoff=MAY.handoff + HANDOFF_BAND),
                        seed)
        rows.append({
            "month": name, "agent": agent,
            "outcomes": mid["verified"],
            "low": lo["per_outcome"], "mid": mid["per_outcome"],
            "high": hi["per_outcome"],
            "bill_low": lo["total"], "bill_mid": mid["total"],
            "bill_high": hi["total"],
            "naive_bill": ACTUAL["May 2026"] * mid["verified"],
            "actual": ACTUAL.get(name),
        })
    return rows


def step_drift(seed: int = 18, drifts=(0.0, 0.15, 0.30, 0.60)):
    """How far steps per attempt can drift before the model line, not
    the people lines, decides the bill."""
    out = []
    for d in drifts:
        c = month_cost(with_levers(MAY, token_scale=1.0 + d,
                                   retry_scale=1.0 + d), seed)
        out.append((d, c["lines"]["model tokens"], c["per_outcome"]))
    return out
