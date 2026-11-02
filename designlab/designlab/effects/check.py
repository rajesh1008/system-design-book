"""The ledger checker: two witnesses for every effect (Section 3).

The ledger says what we believe happened. The supplier's own record
(its reservation history, folio or settlement file) says what did. The
checker reads both and reports:

    duplicates   one business intent with more than one supplier effect
    unbacked     a committed ledger entry with no supplier effect
    orphans      a supplier effect with no committed entry behind it
    for_people   escalated entries, each with what the supplier shows

It never repairs anything. It only counts, so the count can fail a test.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from corpus.tools import SupplierSim
from .ledger import Ledger


@dataclass
class Report:
    intents: int = 0
    effects: int = 0
    duplicates: int = 0
    unbacked: int = 0
    orphans: int = 0
    for_people: int = 0
    people_find_applied: int = 0
    duplicate_intents: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.duplicates == 0 and self.unbacked == 0

    def lines(self) -> list[str]:
        return [f"intents {self.intents:,}, supplier effects "
                f"{self.effects:,}",
                f"duplicates {self.duplicates}, unbacked "
                f"{self.unbacked}, orphans {self.orphans}",
                f"escalated to a person {self.for_people} "
                f"({self.people_find_applied} applied at supplier)",
                "checker: " + ("PASS" if self.ok else "FAIL")]


def check(sims: dict[str, SupplierSim], intents: int,
          ledger: Ledger | None = None) -> Report:
    r = Report(intents=intents)
    per_intent: dict[tuple[str, str], int] = {}
    by_ref: dict[str, int] = {}
    for sim in sims.values():
        for rec in sim.records:
            r.effects += 1
            slot = (sim.tool.name, rec["request"]["intent"])
            per_intent[slot] = per_intent.get(slot, 0) + 1
            if rec["ref"]:
                by_ref[rec["ref"]] = by_ref.get(rec["ref"], 0) + 1
    for (tool, intent), n in sorted(per_intent.items()):
        if n > 1:
            r.duplicates += n - 1
            r.duplicate_intents.append(f"{tool}:{intent}")
    if ledger is not None:
        for key, e in ledger.entries.items():
            seen = by_ref.get(key, 0)
            if e.state == "committed" and seen == 0 \
                    and e.receipt and e.receipt.get("effect_id"):
                r.unbacked += 1
            if e.state == "escalated":
                r.for_people += 1
                r.people_find_applied += 1 if seen else 0
            if e.state in ("failed", "abandoned") and seen:
                r.orphans += seen
    return r
