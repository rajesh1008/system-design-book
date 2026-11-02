"""Finding every rebooking that used a memory (the first hour).

The trail records which memory ids each context packet carried
(Chapter 21's packet log, Chapter 22's ids). The search runs on ids,
not on words: "prefers Denver" was restated in the pinned slot without
its id, so a text search for the pin would miss runs where the words
differ, and an id search finds every packet the note entered.
"""
from __future__ import annotations

from collections import Counter

from .expiry import classify


def used_memory(runs: list[dict], memory_id: str) -> list[dict]:
    return [r for r in runs if memory_id in r["packet_notes"]]


def wrong_city(runs: list[dict], itins: list[dict]) -> list[dict]:
    dest = {i["itinerary_id"]: i["destination"] for i in itins}
    return [r for r in runs if r["proposal_dest"]
            and r["proposal_dest"] != dest[r["itinerary_id"]]]


def place_notes(history: list[dict]) -> list[dict]:
    """Earlier runs whose packet held a note that names a place."""
    return [h for h in history if classify(h["note"]) == "destination"]


def dispositions(runs: list[dict]) -> Counter:
    return Counter(r["disposition"] for r in runs)
