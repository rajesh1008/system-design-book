"""The grounding checker. A claim is grounded when the passage it cites
is admissible for the question: a rule or notice, from the carrier and
topic the claim is about, in effect on the case's as-of date, and the
value the claim states is the value that passage gives. A citation to a
superseded page that says exactly what the claim says is not grounded;
that is the opening of Chapter 19.
"""
from __future__ import annotations

from .agentic import admissible


def check(task, answer: list) -> list[tuple]:
    out = []
    for slot, doc in answer:
        if doc is None:
            out.append((slot, None, "no citation"))
        elif doc.kind not in ("fare-rule", "notice"):
            out.append((slot, doc, f"cites a {doc.kind}"))
        elif doc.carrier != slot.carrier:
            out.append((slot, doc, "other carrier"))
        elif doc.topic != slot.topic:
            out.append((slot, doc, "other topic"))
        elif not doc.in_effect(task.as_of):
            out.append((slot, doc, "not in effect"))
        else:
            assert admissible(doc, slot, task.as_of)
            out.append((slot, doc, "grounded"))
    return out


def rate(runs) -> tuple[int, int]:
    good = total = 0
    for r in runs:
        for _, _, verdict in check(r.task, r.answer):
            total += 1
            good += verdict == "grounded"
    return good, total
