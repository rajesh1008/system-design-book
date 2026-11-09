"""Chapter 45's record rule: an internal design's record is a review
record (Chapter 42), not only a method record (Chapter 5).

Chapter 5's record needs an owner, evidence, and a reversal condition.
Chapter 42's review record also needs a signer who is not the owner,
a reason each losing option lost, and a revisit date and trigger.
This rule builds review.record.Record from the design's [record] and
[decision] blocks and runs Chapter 42's validator on it.

    RVW-1  the review validator refuses the record, its revisit date
           is not after the design's as-of date, or it falls in a
           month that already holds seven revisits in the record store

Chapter 43's six records carry no signer or revisit date; the rule
applies to internal designs only, and bringing the six under it is
left to their owners.
"""
from __future__ import annotations

import tomllib
from collections import Counter
from pathlib import Path

from method.lint import Finding
from review.record import Option, Record, validate

from .privilege import internal

STORE = Path(__file__).resolve().parents[1] / "review" / "data" / \
    "records.toml"
MONTH_FULL = 7


def store() -> list[dict]:
    return tomllib.loads(STORE.read_text())["records"]


def due_by_month(records: list[dict] | None = None) -> Counter:
    records = store() if records is None else records
    return Counter(r["revisit_date"][:7] for r in records
                   if r.get("revisit_date")
                   and r.get("status") != "revisited")


def to_record(spec: dict) -> Record:
    rec = spec.get("record", {})
    dec = spec.get("decision", {})
    opts = [Option(o["name"], o["name"] == dec.get("chosen"),
                   o.get("why_not", ""))
            for o in dec.get("options", [])]
    cons = rec.get("consequences", [])
    return Record(
        id=rec.get("id", ""), review=rec.get("review", ""),
        title=rec.get("title", ""), date=rec.get("date", ""),
        owner=rec.get("owner", ""), signer=rec.get("signer", ""),
        context=rec.get("context", ""), options=opts,
        decision=rec.get("decision", ""),
        evidence=list(rec.get("evidence", [])),
        consequences=[cons] if isinstance(cons, str) else list(cons),
        revisit_date=rec.get("revisit_date", ""),
        revisit_trigger=rec.get("revisit_trigger", ""))


def rvw_1(spec: dict) -> list[Finding]:
    if not internal(spec):
        return []
    r = to_record(spec)
    w = f"record {r.id or '?'}"
    out = [Finding("RVW-1", w, p) for p in validate(r)]
    as_of = spec["design"].get("as_of", "")
    if r.revisit_date and r.revisit_date <= as_of:
        out.append(Finding("RVW-1", w, f"revisit {r.revisit_date} is "
                           f"not after {as_of}"))
    month = r.revisit_date[:7]
    if month and due_by_month()[month] >= MONTH_FULL:
        out.append(Finding("RVW-1", w, f"{month} already holds "
                           f"{due_by_month()[month]} revisits"))
    return out
