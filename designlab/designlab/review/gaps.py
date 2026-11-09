"""The five gap questions, asked of a design that acts.

The procedure has four steps: walk the evidence chain, ask the five
gap questions, run the checklist, record the decision. Each question
is answered by checklist items; a question is answered only when all
of its items pass.
"""
from __future__ import annotations

from . import checklist
from .submission import Submission

# gap id, link, the question, items that answer it
GAPS = [
    ("G1", "output to proposal",
     "What does it propose, and in what typed form?", ("A1",)),
    ("G2", "proposal to permission",
     "Who permits it, outside the loop, by which signed rule?",
     ("C1", "C2", "C4")),
    ("G3", "permission to execution",
     "What makes a retry the same request; what ends the run?",
     ("A2", "A3", "C3")),
    ("G4", "execution to verified outcome",
     "What checks the outcome that did not act?", ("T1", "T2")),
    ("G5", "verified outcome to business result",
     "Which number says it worked, and who owns it?", ("T3",)),
]

CHAIN = ["output", "proposal", "permission", "execution",
         "verified outcome", "business result"]

STEPS = ["walk the chain", "ask the five gap questions",
         "run the checklist", "record the decision"]


def walk(sub: Submission) -> list[tuple[str, str, bool, list[str]]]:
    """(gap, question, answered, problems) for each of the five."""
    results = {r.item.id: r for r in checklist.run(sub)}
    out = []
    for gid, _link, q, items in GAPS:
        probs = [f"{i}: {p}" for i in items for p in results[i].problems]
        out.append((gid, q, not probs, probs))
    return out
