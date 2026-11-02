"""What a leaked credential is worth, by lifetime and by reach.

A token leaks at a uniform moment of its life: into a trace, a log
line, a pasted transcript. Whoever finds it tries it after a delay
drawn from a log-normal with a 45-minute median (an assumption, not a
measurement; change it with --median). It works if it is still alive.
Exposure is reach times the minutes it stays usable after first use:
itinerary-minutes. A per-run token reaches one itinerary; the standing
account reached every customer's. Lakeshore figures are illustrative.
"""
from __future__ import annotations

import math

from common.rand import seeded

LIFETIMES_MIN = (5, 15, 60, 240, 1440)
STANDING_MIN = 225 * 1440


def simulate(lifetime_min: float, leaks: int = 1000,
             median_min: float = 45.0, sigma: float = 1.0,
             seed: int = 32) -> dict:
    rng = seeded(seed, "identity", "exposure", str(lifetime_min))
    mu = math.log(median_min)
    accepted = 0
    usable = 0.0
    for _ in range(leaks):
        at = rng.uniform(0, lifetime_min)
        found = at + rng.lognormvariate(mu, sigma)
        if found < lifetime_min:
            accepted += 1
            usable += lifetime_min - found
    return {"lifetime_min": lifetime_min, "accepted": accepted,
            "leaks": leaks,
            "usable_min": usable / accepted if accepted else 0.0}


def table(median_min: float = 45.0) -> list[dict]:
    rows = [simulate(m, median_min=median_min) for m in LIFETIMES_MIN]
    rows.append(simulate(STANDING_MIN, median_min=median_min))
    return rows


def curve(points: int = 60, median_min: float = 45.0) -> list[tuple]:
    """(lifetime minutes, share accepted) on a log grid, for Fig 32.5."""
    out = []
    for i in range(points):
        m = 10 ** (0 + 4 * i / (points - 1))   # 1 min to 10,000 min
        r = simulate(m, leaks=2000, median_min=median_min)
        out.append((m, r["accepted"] / r["leaks"]))
    return out
