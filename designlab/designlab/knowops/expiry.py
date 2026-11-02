"""Expiry by memory type (memory-retention-v2) and review of legacy
notes against it.

A memory is a claim with a date. How long it stays true depends on
what it is about: a seat preference lasts years, a destination
preference lasts about as long as one trip. Subjects the booking record
owns are never remembered at all; see memory.supersede.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from memory.supersede import RECORD_SUBJECTS

RETENTION_V2 = {          # days, standing scope; trip scope ends with trip
    "seat": 365, "meal": 365, "accessibility": 365,
    "contact": 180, "departure-time": 180,
    "destination": 30, "route": 30,
}
DEFAULT_DAYS = 180

CITIES = ("denver", "phoenix", "chicago", "boston", "miami", "mesa",
          "o'hare", "midway", "minneapolis", "dallas", "cambridge")
_WORDS = (("seat", ("aisle", "window", "seat")),
          ("meal", ("meal", "vegetarian", "kosher")),
          ("contact", ("text me", "call", "email")),
          ("departure-time", ("morning", "red-eye", "evening")),
          ("destination", CITIES))


def ttl_for(subject: str | None) -> int:
    return RETENTION_V2.get(subject or "", DEFAULT_DAYS)


def classify(text: str) -> str | None:
    """The subject a legacy note is about, from its words; None if the
    words do not say. Destination wins over everything else, because
    it is the subject the record owns."""
    low = text.lower()
    if any(c in low for c in CITIES):
        return "destination"
    for subject, words in _WORDS:
        if any(w in low for w in words):
            return subject
    return None


def review_legacy(note: dict, now: datetime, booking: dict | None = None):
    """What memory-retention-v2 does with one legacy note at `now`.

    Returns (action, reason): 'supersede' when a booking record owns the
    subject, 'expire' when the note is older than its type allows,
    'keep' otherwise. A note with no subject is kept only as a prompt
    for a person to confirm, never as a constraint.
    """
    subject = note.get("subject") or classify(note["fact"])
    created = datetime.fromisoformat(note["created_at"])
    age = (now - created).days
    if booking and subject in RECORD_SUBJECTS and subject in booking:
        return ("supersede", f"{subject} is held by the booking record "
                f"({booking[subject]})")
    if age >= ttl_for(subject):
        return ("expire", f"{subject or 'unknown'} note is {age} days "
                f"old; limit {ttl_for(subject)}")
    if subject is None:
        return ("confirm", "no subject; ask before using")
    return ("keep", f"{subject}, {age} days old")


def expiry_of(subject: str | None, observed: datetime) -> datetime:
    return observed + timedelta(days=ttl_for(subject))
