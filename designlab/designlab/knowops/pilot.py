"""The rebooking packet on May 19, 2026, and the same packet fixed.

Two changes, each correct alone, met in this packet. The legacy adapter
(live May 4) handed pilot notes to the memory slot in Chapter 22's
block format. Pinned compaction (live May 18, Chapter 21) extracted
"customer constraints" from the customer's turns and from that block,
and restated them in the pinned slot, near the end of every step. The
note lost its provenance on the way: the pin says "customer
constraint", not "memory MEM-60417, written November 19, 2025".

`packet(itin, mode)` builds the parts and runs Chapter 21's assembler.
`replay_choice` is the replay planner: a rule that reproduces the
choices the trail recorded on May 19 (pick the earliest option that
honors a pinned customer constraint naming a city, else the earliest
option to the destination of record). The live check in knowops.live
asks a real model the same question.
"""
from __future__ import annotations

from context.assemble import assemble
from context.slots import Item, clock_item, stable_items
from corpus.fall2 import (CANCELED, CITY, EVENT_ID, NOTE_ID, NOTE_TEXT,
                          OPTIONS, clock)
from memory.render import tokens

CITY_NAMES = {"DEN": "Denver", "PHX": "Phoenix"}


def options_for(origin: str) -> list[tuple]:
    rows = [o for o in OPTIONS if o[1] == origin and o[0] not in CANCELED]
    return sorted(rows, key=lambda o: (o[3], o[4]))


def option_lines(origin: str) -> list[str]:
    out = []
    for letter, (f, o, d, day, t, _) in zip("ABCDE", options_for(origin)):
        when = "today" if day.endswith("19") else "tomorrow"
        out.append(f"{letter}. {f} {o}-{d} ({CITY_NAMES[d]}) {when} "
                   f"{clock(t)[:5]}")
    return out


def task_text(itin: dict) -> str:
    flight = itin["segments"][0]
    return (f"Rebook itinerary {itin['itinerary_id']}, traveler "
            f"{itin['traveler']}: {itin['origin']} to "
            f"{itin['destination']} on {flight}, canceled "
            f"({EVENT_ID}). Same-carrier options:\n"
            + "\n".join(option_lines(itin["origin"])))


def _item(slot: str, key: str, text: str, rank: int = 0) -> Item:
    return Item(slot, key, tokens(text), rank, text)


def packet(itin: dict, mode: str = "pilot", note: str = NOTE_TEXT,
           trail=None):
    """mode 'pilot' is May 19; mode 'fixed' is DR-24.1 (June 2)."""
    parts = {s: [] for s in ("tools", "instructions", "policy",
                             "examples", "task", "memory", "history",
                             "retrieved", "pinned", "clock")}
    release = "v8" if mode == "pilot" else "v9"
    for it in stable_items("rebook", release):
        parts[it.slot].append(it)
    parts["task"].append(_item("task", itin["itinerary_id"],
                               task_text(itin)))
    if mode == "pilot":
        parts["memory"].append(_item(
            "memory", NOTE_ID, f"customer notes (1):\n  {note}"))
        parts["pinned"].append(_item(
            "pinned", "constraints",
            f"customer constraints (pinned):\n  {note}"))
    else:
        dest = itin["destination"]
        parts["pinned"].append(_item(
            "pinned", "record",
            f"destination of record: {dest} (booking "
            f"{itin['itinerary_id']}; a change of city needs the "
            f"customer's own request in this session)"))
    parts["clock"].append(clock_item("2026-05-19T11:31:00-05:00"))
    return assemble(parts, trail=trail, run=itin["itinerary_id"])


def where(asm, needle: str) -> list[tuple[str, int]]:
    """(slot, token offset) of each item whose text holds `needle`."""
    out, at = [], 0
    for it in asm.items:
        if needle in it.text:
            out.append((it.slot, at))
        at += it.tokens
    return out


def replay_choice(itin: dict, asm) -> tuple[str, str]:
    """(flight, why), as the trail recorded the pilot's choices."""
    opts = options_for(itin["origin"])
    pinned = " ".join(i.text for i in asm.items if i.slot == "pinned")
    for f, _, d, _, _, _ in opts:
        if "constraint" in pinned and CITY_NAMES[d] in pinned:
            return f, "honors stated preference"
    for f, _, d, _, _, _ in opts:
        if d == itin["destination"]:
            return f, "earliest seat to the destination of record"
    return "", "no option"


def fixed_choice(itin: dict, asm) -> tuple[str, str]:
    """DR-24.1: options are filtered to the destination of record
    before the planner sees a choice; a city change goes to the desk."""
    for f, _, d, _, _, _ in options_for(itin["origin"]):
        if d == itin["destination"]:
            return f, "earliest seat to the destination of record"
    return "", "desk"
