"""Two back-office calculations for Chapter 45's reconciliation design.

tolerance_trial() matches a synthetic month of settlement lines to a
booking ledger twice: at the signed tolerance (exact amount, one day)
and at a widened one (0.5% and three days). Every line carries the id
of the booking it truly settles, so a match to any other booking is
a false match: it consumes a counterpart that belonged to someone
else. lanes() works out, for a set of breaks sorted into lanes, which
lane decides when recovery ends. Deterministic (seed 45). The data
is synthetic and Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

@dataclass(frozen=True)
class Trial:
    lines: int
    matched: int
    false: int
    absorbed_usd: float

    @property
    def rate(self) -> float:
        return self.matched / self.lines


def month_of_lines(n: int = 10000, seed: int = 45):
    """Bookings (id, amount, day) and settlement lines (ref, truth,
    amount, day). ref is the ticket number the airline printed, None
    when it is missing; truth is the booking the line really settles,
    None for a duplicate charge."""
    rng = random.Random(seed)
    books, lines = [], []
    for i in range(n):
        amt = round(rng.uniform(60, 900), 2)
        day = rng.randrange(30)
        books.append((i, amt, day))
        r = rng.random()
        lag = rng.randrange(2)
        if r < 0.930:                      # clean
            lines.append((i, i, amt, day + lag))
        elif r < 0.955:                    # timing: 2-3 days late
            lines.append((i, i, amt, day + 2 + lag))
        elif r < 0.975:                    # fee difference, 0.1%-0.5%
            fee = round(amt * rng.uniform(0.001, 0.005), 2)
            lines.append((i, i, round(amt - fee, 2), day + lag))
        elif r < 0.990:                    # ticket number missing
            lines.append((None, i, amt, day + lag))
        elif r < 0.995:                    # duplicate charge
            lines.append((i, i, amt, day + lag))
            lines.append((None, None, amt, day + rng.randrange(4)))
        # else: the airline has not settled it yet
    lines.sort(key=lambda x: x[3])
    return books, lines


def _fits(b, amt, day, pct, days) -> bool:
    return (abs(b[1] - amt) <= b[1] * pct + 1e-9
            and 0 <= day - b[2] <= days)


def match(books, lines, pct: float, days: int) -> Trial:
    """A line with a ticket number matches that booking if it fits;
    one without matches the closest open booking that fits."""
    open_ = {b[0]: b for b in books}
    matched = false = 0
    absorbed = 0.0
    for ref, truth, amt, day in lines:
        if ref is not None:
            b = open_.get(ref)
            b = b if b and _fits(b, amt, day, pct, days) else None
        else:
            fits = [x for x in open_.values()
                    if _fits(x, amt, day, pct, days)]
            b = min(fits, key=lambda x: (abs(x[1] - amt), day - x[2]),
                    default=None)
        if b:
            del open_[b[0]]
            matched += 1
            false += b[0] != truth
            absorbed += abs(b[1] - amt)
    return Trial(len(lines), matched, false, absorbed)


def tolerance_trial():
    """The signed tolerance against the widened one."""
    books, lines = month_of_lines()
    return (match(books, lines, 0.0, 1), match(books, lines, 0.005, 3))


@dataclass(frozen=True)
class Lane:
    name: str
    breaks: int
    minutes: float
    staff: int
    value_usd: float

    @property
    def hours(self) -> float:
        return self.breaks * self.minutes / 60 / self.staff


# The September 14, 2026 settlement week, the week after the storm.
STORM_WEEK = (
    Lane("timing", 120, 2, 6, 180.0),
    Lane("reference", 180, 12, 6, 240.0),
    Lane("duplicate charge", 60, 45, 2, 640.0),
)


def lanes(rows=STORM_WEEK) -> dict:
    """Generalists share the first lanes; a specialist lane runs on
    its own people in parallel."""
    general = [r for r in rows if r.staff == rows[0].staff]
    special = [r for r in rows if r.staff != rows[0].staff]
    g_hours = sum(r.breaks * r.minutes for r in general) / 60 \
        / rows[0].staff
    s_hours = max((r.hours for r in special), default=0.0)
    total_v = sum(r.breaks * r.value_usd for r in rows)
    left_v = sum(r.breaks * r.value_usd for r in special)
    return {"general_hours": g_hours, "special_hours": s_hours,
            "breaks": sum(r.breaks for r in rows),
            "cleared_by_count": sum(r.breaks for r in general)
            / sum(r.breaks for r in rows),
            "value_total": total_v, "value_left": left_v}
