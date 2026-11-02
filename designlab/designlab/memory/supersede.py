"""Supersession by records of fact (Chapter 24).

Some subjects have an owner outside memory: the booking system holds
the destination, the origin, the dates, the travelers, and the carrier
of every itinerary. A memory about one of those subjects is never read
into a task that has a booking record; the record wins, the memory is
kept out of the packet, and the reason goes to the trail. This is
supersession at read time. Nothing is deleted, so the memory's history
and provenance stay where Chapter 22 put them.

    kept, dropped = by_record(records, booking, trail)
"""
from __future__ import annotations

RECORD_SUBJECTS = ("destination", "origin", "dates", "travelers",
                   "carrier")


def by_record(records, booking: dict, trail=None):
    """Split memories into (kept, superseded) against one booking.

    `booking` maps record subjects to the values of record, and must
    name its `record_id`. Each superseded entry is (memory, subject,
    value of record).
    """
    kept, superseded = [], []
    for r in records:
        subject = getattr(r, "subject", None)
        if subject in RECORD_SUBJECTS and subject in booking:
            superseded.append((r, subject, booking[subject]))
            if trail is not None:
                trail.append({"kind": "memory.superseded_by_record",
                              "memory_id": r.memory_id,
                              "subject": subject,
                              "record": booking.get("record_id"),
                              "value_of_record": booking[subject]})
        else:
            kept.append(r)
    return kept, superseded
