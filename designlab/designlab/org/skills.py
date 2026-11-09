"""Six skills, four planes, and the gap analysis (section 3).

A skill is covered when at least two seated people other than the
lead hold it at level 2 or higher. The lead does not count: the lead
is the escalation path, and a plane that only the lead can work on
stops when the lead is on leave. The rule is the team's, written in
the charter; change MIN_DEPTH or the lead exclusion and the gaps move.
"""
from __future__ import annotations

from datetime import date

from .roles import AS_OF, SEATS, seated

SKILLS = ("distributed", "models", "retrieval", "control",
          "evaluation", "operations")

# Where each skill does its work. Operations touches every plane.
PLANES = {
    "distributed": ("action", "trail"),
    "models": ("action",),
    "retrieval": ("knowledge",),
    "control": ("control",),
    "evaluation": ("trail",),
    "operations": ("action", "control", "knowledge", "trail"),
}

MIN_LEVEL = 2
MIN_DEPTH = 2


def coverage(day: date = AS_OF, seats=SEATS,
             count_lead: bool = False) -> dict[str, list[str]]:
    """Skill -> holders at MIN_LEVEL or above among seated people."""
    out: dict[str, list[str]] = {k: [] for k in SKILLS}
    for s in seated(day, seats):
        if s.key == "lead" and not count_lead:
            continue
        for k, lvl in zip(SKILLS, s.levels):
            if lvl >= MIN_LEVEL:
                out[k].append(s.holder)
    return out


def gaps(day: date = AS_OF, seats=SEATS, **kw) -> list[str]:
    cov = coverage(day, seats, **kw)
    return [k for k in SKILLS if len(cov[k]) < MIN_DEPTH]


def with_seat(seat, seats=SEATS) -> tuple:
    """The roster with `seat` replacing the seat of the same key."""
    return tuple(seat if s.key == seat.key else s for s in seats)
