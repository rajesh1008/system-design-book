"""Daily counts for the rebooking slice, June 1 to August 31, 2026.

Agent-path rebookings a day grow with the agent's share (14% of
changes in June, 27% in July, 36% in August), and the ordinary rate
of unverified outcomes falls as the platform matures. July 8 adds the
forty reissues on the old flight number. Seeded (37); the counts are
synthetic and Lakeshore figures are illustrative.
"""
from __future__ import annotations

from datetime import date, timedelta

from common.rand import seeded

from . import july8

FIRST, LAST = date(2026, 6, 1), date(2026, 8, 31)
PER_DAY = {6: 300, 7: 560, 8: 750}
ORDINARY = {6: 0.0042, 7: 0.0040, 8: 0.0030}
INCIDENT = {date(2026, 7, 8)}


def series(seed: int = 37, pinned: bool = False) -> list[tuple]:
    """[(day, rebookings, unverified)]; `pinned` replays July as if the
    classifier had been pinned to its dated June model."""
    rng = seeded(seed, "daily")
    out, d = [], FIRST
    while d <= LAST:
        n = int(PER_DAY[d.month] * rng.uniform(0.9, 1.1))
        if d in INCIDENT:
            # the replayed window, then the rest of the day as usual
            w = july8.summary(july8.build(pinned=pinned))
            rest = n - w["rebookings"]
            bad = (w["rebookings"] - w["rebook_verified"]
                   + sum(rng.random() < ORDINARY[d.month]
                         for _ in range(rest)))
        else:
            bad = sum(rng.random() < ORDINARY[d.month]
                      for _ in range(n))
        out.append((d, n, bad))
        d += timedelta(days=1)
    return out


def rolling(rows, days: int = 28, target: float = 0.99):
    """[(day, eligible, bad, budget, used)] over trailing windows."""
    out = []
    for i in range(days - 1, len(rows)):
        win = rows[i - days + 1:i + 1]
        n = sum(r[1] for r in win)
        bad = sum(r[2] for r in win)
        budget = (1 - target) * n
        out.append((rows[i][0], n, bad, budget, bad / budget))
    return out


def on(rows, day: date):
    for r in rolling(rows):
        if r[0] == day:
            return r
    raise KeyError(day)

