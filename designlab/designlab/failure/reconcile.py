"""Reconciliation against the processor's record (Sections 3 and 5).

The ledger says what Lakeshore believes it paid. The processor's
refund list (intraday) and settlement file (next morning) say what
was paid. `reconcile` reads both and counts; it never repairs.

    duplicates   credits beyond the first on one charge
    missing      charges owed a refund that got none
    orphans      credits with no ledger entry behind them

`ratio_alert` is the check that fired on April 14: every 30 minutes,
credits over distinct refunded charges in the last cut window.
`interval_scan` is the fix: look for a second credit on any charge
every few minutes, and stop the path at the first one.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Report:
    owed: int = 0
    credits: int = 0
    charges_paid: int = 0
    duplicates: int = 0
    duplicate_usd: float = 0.0
    paid_twice: int = 0
    paid_three: int = 0
    missing: int = 0
    orphans: int = 0
    duplicate_charges: list[str] = field(default_factory=list)


def reconcile(lines: list[dict], owed: dict[str, float],
              ledger_refs: set[str]) -> Report:
    by_charge: dict[str, list[dict]] = defaultdict(list)
    for ln in lines:
        by_charge[ln["charge_id"]].append(ln)
    r = Report(owed=len(owed), credits=len(lines),
               charges_paid=len(by_charge))
    for charge, cs in sorted(by_charge.items()):
        if len(cs) > 1:
            r.duplicates += len(cs) - 1
            r.duplicate_usd += cs[0]["amount_usd"] * (len(cs) - 1)
            r.duplicate_charges.append(charge)
            r.paid_twice += len(cs) == 2
            r.paid_three += len(cs) == 3
    r.duplicate_usd = round(r.duplicate_usd, 2)
    r.missing = sum(1 for c in owed if c not in by_charge)
    r.orphans = sum(1 for ln in lines if ln["ref"] not in ledger_refs)
    return r


def extra_credits(lines: list[dict]) -> list[dict]:
    """The second and later credit on each charge, in time order."""
    seen: set[str] = set()
    out = []
    for ln in sorted(lines, key=lambda x: x["at"]):
        if ln["charge_id"] in seen:
            out.append(ln)
        seen.add(ln["charge_id"])
    return out


def ratio_alert(lines: list[dict], runs: list[float],
                window_s: float = 1800.0, cut_s: float = 120.0,
                threshold: float = 1.05) -> list[dict]:
    rows = []
    for run in runs:
        hi = run - cut_s
        lo = hi - window_s
        w = [ln for ln in lines if lo <= ln["at"] < hi]
        charges = {ln["charge_id"] for ln in w}
        ratio = len(w) / len(charges) if charges else 0.0
        rows.append({"run": run, "from": lo, "to": hi, "credits": len(w),
                     "charges": len(charges), "ratio": round(ratio, 3),
                     "fired": ratio > threshold})
    return rows


def interval_scan(lines: list[dict], every_s: float, start: float,
                  end: float) -> dict:
    """Run a duplicate scan every `every_s` from `start`. Returns the
    first run that sees a second credit, and how many extra credits
    were paid by then (with the path stopped at that run)."""
    extras = extra_credits(lines)
    t = start
    while t <= end:
        seen = [x for x in extras if x["at"] < t]
        if seen:
            return {"every_s": every_s, "flag_at": t,
                    "paid_before": len(seen),
                    "usd_before": round(sum(x["amount_usd"]
                                            for x in seen), 2)}
        t += every_s
    return {"every_s": every_s, "flag_at": None, "paid_before": 0,
            "usd_before": 0.0}
