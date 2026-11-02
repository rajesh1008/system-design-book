"""Count changes, not contacts.

A contact is anything a customer started: a call, a chat, an email, a
self-service session. A change is a distinct edit to a booking, found in
the booking system's change log. Follow-up contacts about a change that
is already open are contacts, not new changes.
"""
from __future__ import annotations

from collections import Counter

from corpus.ops import CHANGE_MIX, WEIGHTS


def naive_count(t: dict) -> dict:
    """The failure: every contact counted as a unit of work."""
    w = WEIGHTS["ops_contacts"]
    return {"units": len(t["ops_contacts"]) * w,
            "source": "contact log, all reasons"}


def count_changes(t: dict) -> dict:
    wc, wch = WEIGHTS["ops_contacts"], WEIGHTS["ops_changes"]
    contacts = t["ops_contacts"]
    reasons = Counter(c["reason"] for c in contacts)
    about_change = [c for c in contacts if c["change_id"]]
    distinct = {c["change_id"] for c in about_change}
    log = {c["change_id"] for c in t["ops_changes"]}
    if distinct != log:
        raise ValueError("contact log and change log disagree: "
                         f"{len(distinct ^ log)} change ids")
    changes = t["ops_changes"]
    by_type = Counter(c["type"] for c in changes)
    by_group = Counter(c["group"] for c in changes)
    by_handler = Counter(c["handled_by"] for c in changes)
    person_by_type = Counter(c["type"] for c in changes
                             if c["handled_by"] == "person")
    return {
        "contacts": len(contacts) * wc,
        "contacts_by_reason": {k: v * wc for k, v in reasons.items()},
        "contacts_about_a_change": len(about_change) * wc,
        "follow_ups": reasons["change-follow-up"] * wc,
        "changes": len(changes) * wch,
        "by_type": {k: by_type[k] * wch for k in CHANGE_MIX},
        "by_group": {k: v * wch for k, v in by_group.items()},
        "person_share_by_type": {
            k: person_by_type[k] / by_type[k] for k in CHANGE_MIX},
        "by_handler": {k: v * wch for k, v in by_handler.items()},
        "person_share": by_handler["person"] / len(changes),
        "sources": {"contacts": "contact log (telephony and CRM)",
                    "changes": "booking system change log"},
    }
