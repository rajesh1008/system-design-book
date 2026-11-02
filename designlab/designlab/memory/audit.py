"""The legacy audit: what the pilot's memory notes would become.

The pilot's notes (the corpus `memories` table) were written by the
framework's memory feature from November 3, 2025. They carry a fact,
an extractor tag, sometimes a contact id, and an expiry nobody read.
The audit sorts each note written before the cut-off into one outcome:

    expired       past memory-retention-v1's 180 days on the cut-off
    no source     no contact id to point to (the CRM import)
    inferred      the agent concluded it; held for the desk, not migrated
    session over  tagged for one session that has ended
    confirm       the customer said it; ask before it becomes standing

It also counts notes on subjects the governed store never writes from
inference (refund, health, contact), whatever their source.
"""
from __future__ import annotations

from collections import Counter

PILOT_START = "2025-11-03T00:00:00Z"
CUTOFF = "2026-05-11T05:00:00Z"        # Monday, May 11, 2026, 00:00 CDT

SUBJECT = {"prefers an aisle seat": "seat", "prefers a window seat": "seat",
           "travels with a service animal": "health",
           "needs a ground-floor room": "health",
           "wants refunds to the original card, not credit": "refund",
           "loyalty number on file with the carrier": "contact",
           "asked not to be called before 9:00 a.m.": "contact"}
OUTCOMES = ("expired", "no source", "inferred", "session over", "confirm")


def outcome(note: dict, cutoff: str = CUTOFF) -> str:
    if note["expires_at"] <= cutoff:
        return "expired"
    src = note["provenance"]
    if src["contact_id"] is None:
        return "no source"
    if src["source"] == "agent-inferred":
        return "inferred"
    if note["scope"] == "session":
        return "session over"
    return "confirm"


def audit_legacy(notes: list[dict], cutoff: str = CUTOFF) -> dict:
    window = [n for n in notes if PILOT_START <= n["created_at"] < cutoff]
    by = Counter(outcome(n, cutoff) for n in window)
    high = sum(1 for n in window
               if SUBJECT.get(n["fact"]) in ("refund", "health", "contact"))
    return {"notes": len(window),
            "customers": len({n["customer_id"] for n in window}),
            "outcomes": {k: by.get(k, 0) for k in OUTCOMES},
            "with_scope": 0,          # the pilot's reader honored none
            "high_consequence": high}
