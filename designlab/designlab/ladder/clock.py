"""The clock: four marks, at 5, 15, 30, and 45 minutes.

Chapter 5's clock has eight slices, one per artifact. The interview
clock keeps their order and folds them into four marks an interviewer
can check without a stopwatch: by five minutes the effect is framed
and one number estimated; by fifteen the chain is drawn; by thirty the
five gaps are closed, each with an owner; by forty-five the design is
costed and its decision recorded.
"""
from __future__ import annotations

from method.artifacts import CLOCK as METHOD_CLOCK

from .notes import events

GAPS = ("G1", "G2", "G3", "G4", "G5")

MARKS = (
    (5, "frame and estimate", (0, 1, 2)),
    (15, "draw the chain", (3,)),
    (30, "close the five gaps", (4, 5)),
    (45, "cost and defend", (6, 7)),
)


def slices(mark: int) -> list[str]:
    """Chapter 5's slices that fold into one mark."""
    for m, _, idx in MARKS:
        if m == mark:
            return [METHOD_CLOCK[i][2] for i in idx]
    raise KeyError(mark)


def closed(note: dict, by: int | None = None) -> list[str]:
    seen = {e["gap"] for e in events(note, "gap", by)
            if e.get("owner")}
    return [g for g in GAPS if g in seen]


def framed(note: dict, by: int | None = None) -> bool:
    return any(e.get("effects") for e in events(note, "frame", by))


def check(note: dict) -> list[tuple[int, str, bool, str]]:
    """For each mark: (minute, task, met, what the board shows)."""
    out = []
    f5 = framed(note, 5)
    e5 = bool(events(note, "estimate", 5))
    out.append((5, MARKS[0][1], f5 and e5,
                f"effect {'yes' if f5 else 'no'}, "
                f"number {'yes' if e5 else 'no'}"))
    ch = events(note, "chain", 15)
    out.append((15, MARKS[1][1], bool(ch),
                f"chain {'drawn' if ch else 'not drawn'}"))
    g = closed(note, 30)
    out.append((30, MARKS[2][1], len(g) == 5,
                f"gaps {len(g)} of 5"))
    c = bool(events(note, "cost", 45))
    r = bool(events(note, "record", 45))
    out.append((45, MARKS[3][1], c and r,
                f"cost {'yes' if c else 'no'}, "
                f"record {'yes' if r else 'no'}"))
    return out


def marks_met(note: dict) -> int:
    return sum(1 for _, _, ok, _ in check(note) if ok)
