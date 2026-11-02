"""A finding: what the auditor writes when a control did not hold, and
the only way it closes.

A finding moves opened, contained, triaged, fix live, evidence
submitted, then closed or reopened. The owner moves it up to evidence
submitted. Only the auditor closes it, and only on a verified pack and
a claim that holds on fresh, independent, admissible evidence. A new
rebutting record reopens it. Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import admissible

STATES = ("opened", "contained", "triaged", "fix_live",
          "evidence_submitted", "closed", "reopened")
NEXT = {"opened": ("contained",), "contained": ("triaged",),
        "triaged": ("fix_live",), "fix_live": ("evidence_submitted",),
        "evidence_submitted": ("closed", "fix_live"),
        "closed": ("reopened",), "reopened": ("contained",)}


class Refused(Exception):
    pass


@dataclass
class Finding:
    fid: str
    claim: str
    owner: str
    auditor: str
    state: str = "opened"
    log: list[tuple[str, str, str, str]] = field(default_factory=list)

    def move(self, to: str, on: str, who: str, note: str = "") -> None:
        if to not in NEXT[self.state]:
            raise Refused(f"{self.fid}: {self.state} to {to}")
        if to == "closed":
            raise Refused("use close(), which checks the evidence")
        if to in ("triaged", "contained", "fix_live",
                  "evidence_submitted") and who != self.owner:
            raise Refused(f"{to} is the owner's move, not {who}'s")
        self.state = to
        self.log.append((on, to, who, note))

    def close(self, on: str, who: str, pack_problems: list[str],
              evidence, rebuttals=()) -> None:
        if self.state != "evidence_submitted":
            raise Refused(f"{self.fid}: nothing submitted to close on")
        if who != self.auditor:
            raise Refused(f"only {self.auditor} closes {self.fid}; "
                          f"{who} owns it")
        if pack_problems:
            raise Refused(f"pack does not verify: {pack_problems[0]}")
        ok, why = admissible.holds(evidence, on, rebuttals)
        if not ok:
            raise Refused(f"claim does not hold: {why}")
        self.state = "closed"
        self.log.append((on, "closed", who, why))

    def reopen(self, on: str, who: str, record: admissible.Record) -> None:
        self.move_any("reopened", on, who, f"rebutted by {record.rid}")

    def move_any(self, to, on, who, note):
        if to not in NEXT[self.state]:
            raise Refused(f"{self.fid}: {self.state} to {to}")
        self.state = to
        self.log.append((on, to, who, note))


def f0624() -> Finding:
    return Finding("F-0624-01", admissible.CLAIM, owner="Ben Carter",
                   auditor="Elena Vasquez")


def walk(pack_problems: list[str]) -> tuple[Finding, list[str]]:
    """June 24 to July 3, with the refusals the rules produce."""
    f = f0624()
    f.log.append(("2026-06-24", "opened", "Elena Vasquez",
                  "P-0624-HOTEL reached the desk"))
    out = []
    f.move("contained", "2026-06-24", "Ben Carter",
           "14 notes quarantined; 0 refunds to unpaid forms")
    f.move("triaged", "2026-06-25", "Ben Carter",
           "three causes, two contributing")
    f.move("fix_live", "2026-06-26", "Ben Carter",
           "pb-2026.06.22.2 active; card-on-file v2")
    f.move("evidence_submitted", "2026-07-02", "Ben Carter",
           "pack 2026-06 and E6 to E10")
    for who, ev in (("Ben Carter", admissible.JULY_2),
                    ("Elena Vasquez", admissible.JUNE_24)):
        try:
            f.close("2026-07-03", who, pack_problems, ev,
                    [admissible.REBUTTAL])
        except Refused as e:
            out.append(f"refused: {e}")
    f.close("2026-07-03", "Elena Vasquez", pack_problems,
            admissible.JULY_2, [admissible.REBUTTAL])
    return f, out
