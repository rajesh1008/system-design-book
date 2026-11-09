"""The effect ledger: one entry per key, every attempt recorded (Chapter 7).

States and the moves allowed between them:

    reserved     -> attempting
    attempting   -> committed | unknown | failed
    unknown      -> committed   (found by lookup)
                 -> attempting  (key replay, or lookup says absent)
                 -> escalated   (no way to tell; a person decides)
                 -> abandoned   (at most once: not worth a duplicate)
    committed    -> compensating -> compensated

A lease with a fencing token guards each attempt. A worker that paused
past its lease (waiting for an approval, say) holds a stale token, and
the ledger refuses its writes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .keys import EffectKey

MOVES = {
    "reserved": {"attempting"},
    "attempting": {"committed", "unknown", "failed"},
    "unknown": {"committed", "attempting", "escalated", "abandoned"},
    "committed": {"compensating"},
    "compensating": {"compensated", "escalated"},
    "failed": set(), "escalated": set(), "abandoned": set(),
    "compensated": set(),
}
FINAL = {"committed", "failed", "escalated", "abandoned", "compensated"}


class LedgerConflict(Exception):
    """Same key, different request."""


class StaleLease(Exception):
    """A write from a worker whose lease has passed to another."""


class BadMove(Exception):
    pass


@dataclass
class Entry:
    key: EffectKey
    state: str = "reserved"
    attempts: int = 0
    receipt: Optional[dict] = None
    history: list[tuple[float, str, str]] = field(default_factory=list)
    unknown_since: Optional[float] = None
    resolutions: list[tuple[float, str]] = field(default_factory=list)
    lease_holder: Optional[str] = None
    lease_token: int = 0
    lease_until: float = 0.0


class Ledger:
    def __init__(self) -> None:
        self.entries: dict[str, Entry] = {}

    def reserve(self, ek: EffectKey, now: float) -> tuple[Entry, bool]:
        """Return (entry, new). An existing committed entry means: do not
        call the tool, hand back the stored receipt."""
        e = self.entries.get(ek.key)
        if e is not None:
            if e.key.fingerprint != ek.fingerprint:
                raise LedgerConflict(f"{ek.key}: different request")
            return e, False
        e = Entry(ek)
        e.history.append((now, "reserved", ek.permission_id))
        self.entries[ek.key] = e
        return e, True

    def acquire(self, key: str, holder: str, now: float,
                ttl: float = 30.0) -> int:
        e = self.entries[key]
        if e.lease_holder not in (None, holder) and now < e.lease_until:
            raise StaleLease(f"{key}: lease held by {e.lease_holder}")
        if e.lease_holder != holder or now >= e.lease_until:
            e.lease_token += 1
        e.lease_holder, e.lease_until = holder, now + ttl
        return e.lease_token

    def move(self, key: str, state: str, now: float, note: str = "",
             token: Optional[int] = None) -> Entry:
        e = self.entries[key]
        if token is not None and token != e.lease_token:
            raise StaleLease(f"{key}: token {token}, current "
                             f"{e.lease_token}")
        if state not in MOVES[e.state]:
            raise BadMove(f"{key}: {e.state} -> {state}")
        if e.state == "unknown":
            e.resolutions.append((now - e.unknown_since, state))
            e.unknown_since = None
        if state == "unknown":
            e.unknown_since = now
        if state == "attempting":
            e.attempts += 1
        e.state = state
        e.history.append((now, state, note))
        return e

    def open_unknowns(self) -> list[Entry]:
        return [e for e in self.entries.values() if e.state == "unknown"]

    def by_state(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for e in self.entries.values():
            out[e.state] = out.get(e.state, 0) + 1
        return out
