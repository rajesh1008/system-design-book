"""The rubric: seven criteria, each scored 0, 1, or 2, read from a note.

    framing        the effect named first, with an owner, by minute 5
    estimation     a number with a source that drives the design
    chain          the gate before the effect; a verifier that did not act
    gaps           the five gaps closed, each with an owner
    tradeoffs      at least two options, and why the losers lost
    cost           cost per verified outcome, not per token
    communication  the four marks met and a record that says what
                   reverses it

The checker reads what is on the page. It does not read `right`, the
mark a person puts on an answer that is present and wrong: a rubric
can tell an answer is missing, not that it is right.

An answer clears its level when the total reaches the level's bar,
the five gaps score 2, estimation scores at least 1, the chain scores
at least 1, and every item the prompt must show is shown.

RUBRIC_V0 is the component-list rubric Lakeshore started from: one
point per distinct box named, up to fourteen. It is kept to be beaten.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import clock
from .levels import BY_CODE
from .notes import events, shows
from .prompts import PROMPTS

CRITERIA = ("framing", "estimation", "chain", "gaps", "tradeoffs",
            "cost", "communication")
SHORT = {"framing": "frm", "estimation": "est", "chain": "chn",
         "gaps": "gap", "tradeoffs": "trd", "cost": "cst",
         "communication": "com"}


@dataclass
class Score:
    aid: str
    prompt: str
    level: str
    cells: dict[str, int]
    missing: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(self.cells.values())

    @property
    def cleared(self) -> bool:
        return not self.reasons

    def row(self) -> list[int]:
        return [self.cells[c] for c in CRITERIA]


def framing(note: dict) -> int:
    fr = [e for e in events(note, "frame") if e.get("effects")]
    if not fr:
        return 0
    first = min(fr, key=lambda e: e["at"])
    return 2 if first["at"] <= 5 and first.get("owner") else 1


def estimation(note: dict) -> int:
    est = events(note, "estimate")
    if not est:
        return 0
    if any(e.get("source") and e.get("drives") for e in est):
        return 2
    return 1


def chain(note: dict) -> int:
    ch = events(note, "chain")
    if not ch:
        return 0
    if any(e.get("gate_before_effect") and e.get("verifier_not_actor")
           for e in ch):
        return 2
    return 1


def gaps(note: dict) -> int:
    n = len(clock.closed(note))
    return 2 if n == 5 else 1 if n >= 3 else 0


def tradeoffs(note: dict) -> int:
    tr = events(note, "tradeoff")
    if not tr:
        return 0
    if any(e.get("options", 0) >= 2 and e.get("why_not") for e in tr):
        return 2
    return 1


def cost(note: dict) -> int:
    co = events(note, "cost")
    if not co:
        return 0
    return 2 if any(e.get("unit") == "verified outcome" for e in co) \
        else 1


def communication(note: dict) -> int:
    met = clock.marks_met(note)
    rec = events(note, "record")
    reverse = any(e.get("reverse") for e in rec)
    if met == 4 and reverse:
        return 2
    return 1 if met >= 2 or rec else 0


SCORERS = {"framing": framing, "estimation": estimation, "chain": chain,
           "gaps": gaps, "tradeoffs": tradeoffs, "cost": cost,
           "communication": communication}


def score(note: dict) -> Score:
    a = note["answer"]
    p = PROMPTS[a["prompt"]]
    lv = BY_CODE[p["level"]]
    cells = {c: SCORERS[c](note) for c in CRITERIA}
    shown = shows(note)
    if any(e.get("effects") for e in events(note, "frame", 5)):
        shown.add("effect named")
    missing = [m for m in p["must"] if m not in shown]
    s = Score(a["id"], a["prompt"], lv.code, cells, missing)
    if s.total < lv.bar:
        s.reasons.append(f"total {s.total} under bar {lv.bar}")
    if cells["gaps"] < 2:
        s.reasons.append(f"gaps closed {len(clock.closed(note))} of 5")
    if cells["estimation"] < 1:
        s.reasons.append("no estimate")
    if cells["chain"] < 1:
        s.reasons.append("no chain")
    if missing:
        s.reasons.append("not shown: " + ", ".join(missing))
    return s


def score_v0(note: dict) -> int:
    """The component-list rubric: a point per distinct box, up to 14."""
    names: set[str] = set()
    for e in note.get("said", []):
        names.update(n.lower() for n in e.get("names", []))
    return min(14, len(names))
