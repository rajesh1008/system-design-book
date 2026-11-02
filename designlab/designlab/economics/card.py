"""The economics card, filed Tuesday, September 8, 2026.

Three cells, each read from a record rather than typed: August's cost
per verified outcome from finance's close (reconciled September 4 by
Sarah Whitfield's team), the share of loops with a spend policy at
the gateway, and the July storm replayed under that policy.
"""
from __future__ import annotations

from loops.spec import FARE_WATCH, WAIVER_WATCH

from . import outcome, replay
from .policy import DR38

# The waiver watch's provider spend by Chicago day, August 1 to 31:
# 1.1 to August 9, then 1.2 (14 carriers, options per itinerary).
AUGUST_WAIVER_DAYS = (
    0.36, 0.41, 0.39, 0.35, 0.44, 0.38, 0.37, 0.40, 0.42, 15.46,
    13.54, 16.23, 10.23, 15.99, 13.04, 15.17, 11.17, 12.77, 12.06,
    12.63, 16.25, 13.94, 18.41, 14.94, 11.66, 71.40, 38.20, 15.22,
    14.44, 10.91, 14.42)
REPLAY_WORST_DAY = 64.80          # 1.2 over every notice since June 25
LIVE_LOOPS = (WAIVER_WATCH["loop"], FARE_WATCH["loop"])


def coverage() -> tuple[int, int]:
    covered = {b.loop for b in DR38.loops}
    return sum(1 for x in LIVE_LOOPS if x in covered), len(LIVE_LOOPS)


def cells() -> list[tuple[str, str, str, str]]:
    aug = outcome.close("August")
    lo, _mid, hi = outcome.BAND["August"]
    n, of = coverage()
    capped = replay.run(DR38).billed
    return [
        ("Cost per verified outcome", f"${aug.total:.2f}",
         f"band ${lo:.2f}-{hi:.2f}", "Daniel Price"),
        ("Loops with a spend policy", f"{n / of:.0%}",
         f"{n} of {of} at the gateway", "Ben Carter"),
        ("July storm, replayed", f"${capped:,.0f}",
         "cap; $11,406 as run", "Ben Carter"),
    ]
