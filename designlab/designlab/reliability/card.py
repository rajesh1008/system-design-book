"""The reliability card for Monday, August 31, 2026.

Four lines a decision-maker reads in under a minute, each with the
person who answers for it and the record it is read from.
"""
from __future__ import annotations

from datetime import date

from . import daily, stop
from .objectives import FIVE


def card() -> list[tuple]:
    rows = daily.series()
    _, n, bad, budget, used = daily.on(rows, date(2026, 8, 31))
    times = [stop.july8().seconds, stop.storm().seconds]
    return [
        ("objectives", f"{len(FIVE)}, each from a record the actor "
         "does not write", "Ben Carter"),
        ("error budget", f"verified outcomes, rebooking {used:.0%} "
         f"spent", "Marcus Bell"),
        ("incidents", "2 in July (model update, retry storm)",
         "Ben Carter"),
        ("time to stop", f"median {stop.median(times):.0f} s "
         f"({times[0]:.0f} s, {times[1]:.0f} s)", "Ben Carter"),
    ]
