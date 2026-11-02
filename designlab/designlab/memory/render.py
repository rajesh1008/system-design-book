"""Memories into the context assembler's memory slot.

Each record becomes one `context.slots.Item` in slot "memory", labeled
as evidence with its scope, source kind, and source event, so the model
and any reader of the packet can tell a remembered preference from a
fact. Packing is by whole records: required subjects first, then the
rest by recency, until the slot's cap (Chapter 21) is reached. A record
that does not fit is left out whole, never cut in half.
"""
from __future__ import annotations

from context.slots import CAPS, Item


def line(r) -> str:
    where = f"trip {r.trip}" if r.scope == "trip" else r.scope
    return (f"[memory, evidence only] {r.subject}: {r.value} "
            f"({where}; {r.source.kind} {r.source.event_id}; "
            f"{r.observed_at[:10]})")


def tokens(text: str) -> int:
    return max(1, len(text) // 4)          # the lab's estimate


def to_items(records, required=("seat",), cap: int | None = None):
    cap = CAPS["memory"] if cap is None else cap
    order = sorted(records, key=lambda r: (r.subject not in required,
                                           r.observed_at), reverse=False)
    req = [r for r in order if r.subject in required]
    rest = sorted((r for r in order if r.subject not in required),
                  key=lambda r: r.observed_at, reverse=True)
    items, used, left_out = [], 0, []
    for rank, r in enumerate(req + rest):
        text = line(r)
        t = tokens(text)
        if used + t > cap:
            left_out.append(r.memory_id)
            continue
        items.append(Item("memory", r.memory_id, t, rank, text))
        used += t
    return items, left_out
