"""Which evidence may support a claim, on a given day.

A claim is a sentence an auditor would sign, such as Rachel Morgan's
rule that a refund goes only to a form of payment that paid. Evidence
for it is admissible when it exercised the case the claim is about,
when nothing it depended on changed after it was observed, and when
someone other than the control's owner produced it. Evidence fails in
two different ways. It can be undercut: a change after it was observed
removes the reason to believe it, without showing the claim is false.
Or the claim can be rebutted: a record shows the claim false. Lakeshore
figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass

CLAIM = "A refund goes only to a form of payment that paid."

# Changes that touch what evidence depended on: (day, subject, what).
CHANGES = (
    ("2026-06-12", "refund_ticket schema", "R-0612: refund_to added"),
    ("2026-06-26", "refund policy", "pb-2026.06.22.2 active"),
    ("2026-06-26", "gateway check", "card-on-file v2 live"),
)


@dataclass(frozen=True)
class Evidence:
    eid: str
    what: str
    observed: str          # day it was observed
    subject: str           # what it depended on
    by: str                # who produced it
    owner: str             # who owns the control it is about
    covers: bool           # it exercised the case the claim is about
    bound: bool = True     # approval bound to the exact instrument


@dataclass(frozen=True)
class Record:
    """A record that shows the claim false."""
    rid: str
    what: str
    day: str


JUNE_24 = (
    Evidence("E1", "gate: R-0623 passed 640, refund_other_card 0",
             "2026-06-23", "golden set", "Hannah Clarke's gate",
             "Daniel Price", covers=False),
    Evidence("E2", "battery 2026-06-16 D02: no destination field",
             "2026-06-05", "refund_ticket schema", "Owen's red team",
             "Daniel Price", covers=True),
    Evidence("E3", "card-on-file v1 test: 7731 refused (May 18)",
             "2026-05-18", "refund_ticket schema", "gateway team",
             "gateway team", covers=True),
    Evidence("E4", "bundle pb-2026.06.22 signed by Rachel Morgan",
             "2026-06-22", "refund policy", "Owen's team",
             "Owen's team", covers=False),
    Evidence("E5", "desk approval bound to the proposal digest",
             "2026-06-24", "desk", "refund approver desk",
             "Marcus Bell", covers=True),
)
REBUTTAL = Record("P-0624-HOTEL", "proposal to a card that did not pay "
                  "reached the desk", "2026-06-24")

JULY_2 = (
    Evidence("E6", "bundle pb-2026.06.22.2: destination-v1, "
             "signed, 41 min shadow", "2026-06-26", "refund policy",
             "Rachel Morgan", "Owen's team", covers=True),
    Evidence("E7", "battery 2026-06-26: 62 attacks, 0 effects",
             "2026-06-26", "refund policy", "Owen's red team",
             "Daniel Price", covers=True),
    Evidence("E8", "replay of P-0624-HOTEL: refused before the desk",
             "2026-06-26", "refund policy", "Elena Vasquez",
             "Owen's team", covers=True),
    Evidence("E9", "trail scan Jun 26 to Jul 2: 0 proposals to "
             "unregistered destinations", "2026-07-02", "refund policy",
             "Rachel Morgan's team", "Ben Carter", covers=True),
    Evidence("E10", "card-on-file v2 test reads refund_to",
             "2026-06-26", "gateway check", "gateway team",
             "gateway team", covers=True),
)


def assess(e: Evidence, on: str) -> tuple[str, str]:
    for day, subject, what in CHANGES:
        if subject == e.subject and e.observed < day <= on:
            return "undercut", f"stale since {day}: {what}"
    if not e.covers:
        return "silent", "never exercised the case"
    if not e.bound:
        return "inadmissible", "approval not bound to what ran"
    if e.by == e.owner:
        return "admissible", "but produced by the owner"
    return "admissible", "independent"


def holds(items, on: str, rebuttals=()) -> tuple[bool, str]:
    """The claim holds on a day if no rebuttal stands after the newest
    covering evidence, and independent admissible evidence covers it."""
    good = [e for e in items if assess(e, on) == ("admissible",
                                                  "independent")]
    if not good:
        return False, "no independent admissible evidence"
    newest = max(e.observed for e in good)
    late = [r for r in rebuttals if r.day >= newest]
    if late:
        return False, f"rebutted by {late[0].rid}"
    return True, f"{len(good)} independent items, newest {newest}"
