"""Two onboardings, as Lakeshore logged them.

The desk assistant was onboarded by meeting, before the platform
existed: from Monday, June 22 to Thursday, July 23, 2026, in eleven
meetings. The loyalty assistant was onboarded on the paved road from
Monday, August 17 to Wednesday, August 26, 2026, with one review.
Days are calendar days between the dates. Lakeshore figures are
illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Stage:
    name: str
    start: date
    end: date
    meetings: int
    note: str = ""

    @property
    def days(self) -> int:
        return (self.end - self.start).days


D = date
DESK = (
    Stage("access review", D(2026, 6, 22), D(2026, 6, 26), 2,
          "scopes for the new identity"),
    Stage("registry and narrowing", D(2026, 6, 26), D(2026, 7, 7), 3,
          "which of every tool it kept"),
    Stage("policy", D(2026, 7, 7), D(2026, 7, 14), 3,
          "rules written into the servicing bundle"),
    Stage("evaluation", D(2026, 7, 14), D(2026, 7, 20), 2,
          "a golden set built from scratch"),
    Stage("dashboards", D(2026, 7, 20), D(2026, 7, 23), 1,
          "panels copied from servicing's"),
)
LOYALTY = (
    Stage("template", D(2026, 8, 17), D(2026, 8, 18), 0,
          "the as-built shape's twelve problems closed"),
    Stage("conformance", D(2026, 8, 18), D(2026, 8, 21), 0,
          "K2 failed August 19, old ledger key; fixed August 20"),
    Stage("one review", D(2026, 8, 21), D(2026, 8, 24), 1,
          "registry, bundle, and golden set, Monday, August 24"),
    Stage("shadow and dashboards", D(2026, 8, 24), D(2026, 8, 26), 0,
          "two days in shadow; panels from the template"),
)


def total(stages) -> int:
    return (stages[-1].end - stages[0].start).days


def meetings(stages) -> int:
    return sum(s.meetings for s in stages)
