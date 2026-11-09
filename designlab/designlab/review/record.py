"""The decision record for an agent system, and its validator.

Six parts in order: context, options, decision, evidence,
consequences, revisit. A record also names an owner and a signer who
is not the owner. The validator refuses a record that would not let
a reader a year later reverse the decision for the right reason.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PARTS = ["context", "options", "decision", "evidence",
         "consequences", "revisit"]


@dataclass
class Option:
    name: str
    chosen: bool = False
    why_not: str = ""


@dataclass
class Record:
    id: str
    review: str
    title: str
    date: str
    owner: str = ""
    signer: str = ""
    context: str = ""
    options: list = field(default_factory=list)
    decision: str = ""
    evidence: list = field(default_factory=list)
    consequences: list = field(default_factory=list)
    revisit_date: str = ""
    revisit_trigger: str = ""
    status: str = "active"          # active, revisited
    revisited_on: str = ""
    revisited_by: str = ""


def from_dict(raw: dict) -> Record:
    raw = dict(raw)
    raw["options"] = [Option(**o) for o in raw.get("options", [])]
    return Record(**raw)


def validate(r: Record) -> list[str]:
    """Problems that make a record unusable; empty means it passes."""
    out = []
    if not r.context:
        out.append("REC-CTX no context: what forced the decision")
    chosen = [o for o in r.options if o.chosen]
    if len(r.options) < 2:
        out.append("REC-OPT fewer than two options")
    if len(r.options) >= 2 and len(chosen) != 1:
        out.append("REC-OPT not exactly one option chosen")
    for o in r.options:
        if not o.chosen and not o.why_not:
            out.append(f"REC-OPT {o.name}: no reason it lost")
    if not r.decision:
        out.append("REC-DEC no decision sentence")
    if not r.evidence:
        out.append("REC-EVD no evidence a reader can open")
    if not r.consequences:
        out.append("REC-CON no consequence, cost, or risk named")
    if not (r.revisit_date and r.revisit_trigger):
        out.append("REC-REV needs a revisit date and a trigger")
    if not r.owner:
        out.append("REC-OWN no owner")
    if not r.signer or r.signer == r.owner:
        out.append("REC-SIG signer missing or same as owner")
    return out


# What loyalty's July steering minutes said about partner transfers.
MINUTES = Record(
    id="minutes-2026-07-16", review="", date="2026-07-16",
    title="loyalty steering, item 4",
    decision="Partner transfers approved in principle. AM to proceed.",
    owner="Arjun Mehta")
