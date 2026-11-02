"""A loop that refuses to execute an effect missing any part of its chain record."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from .record import ChainRecord, Refused

ACTOR = "refund-executor"


class Timeout(Exception):
    """The caller stopped waiting. The effect may or may not have happened."""


@dataclass
class CardNetwork:
    """A stand-in for the card network: it applies credits and can be slow.

    `slow_calls` lists call numbers (1-based) whose credit is applied but whose
    response arrives after the caller's timeout, as happened on the Thursday.
    """
    slow_calls: set[int] = field(default_factory=set)
    lost_calls: set[int] = field(default_factory=set)   # never reach the network
    honour_keys: bool = True
    credits: list[dict] = field(default_factory=list)
    _by_key: dict[str, dict] = field(default_factory=dict)
    _calls: int = 0

    def refund(self, itinerary: str, amount_usd: float, key: Optional[str]) -> dict:
        self._calls += 1
        if self._calls in self.lost_calls:
            raise Timeout(f"no response after 8.0 s (call {self._calls})")
        if self.honour_keys and key is not None and key in self._by_key:
            return dict(self._by_key[key], replayed=True)
        credit = {"credit_id": f"CR-{len(self.credits) + 1:05d}",
                  "itinerary": itinerary, "amount_usd": amount_usd}
        self.credits.append(credit)
        if key is not None:
            self._by_key[key] = credit
        if self._calls in self.slow_calls:
            raise Timeout(f"no response after 8.0 s (call {self._calls})")
        return dict(credit, replayed=False)

    def settled(self, itinerary: str) -> list[dict]:
        return [c for c in self.credits if c["itinerary"] == itinerary]


@dataclass
class Trail:
    """Append-only, hash-linked lines. Editing one breaks every later hash."""
    lines: list[str] = field(default_factory=list)

    def append(self, entry: dict) -> str:
        prev = hashlib.sha256(self.lines[-1].encode()).hexdigest()[:12] if self.lines else "genesis"
        line = json.dumps(dict(entry, prev=prev), sort_keys=True)
        self.lines.append(line)
        return line


def settlement_verifier(network: CardNetwork, record: ChainRecord) -> dict:
    """Verify against the settlement file, not against the executor's report."""
    credits = network.settled(record.proposal.itinerary)
    ok = len(credits) == 1 and credits[0]["amount_usd"] == record.proposal.amount_usd
    return {"verified_by": "settlement-reconciler", "credits_found": len(credits), "ok": ok}


@dataclass
class ChainLoop:
    network: CardNetwork
    trail: Trail
    max_attempts: int = 3
    verifier: Callable[[CardNetwork, ChainRecord], dict] = settlement_verifier

    def execute(self, record: ChainRecord) -> ChainRecord:
        missing = record.missing_before_effect(ACTOR)
        if missing:
            self.trail.append({"event": "refused", "missing": missing})
            raise Refused(missing)
        p = record.proposal
        for attempt in range(1, self.max_attempts + 1):
            try:
                record.execution = self.network.refund(p.itinerary, p.amount_usd,
                                                       record.idempotency_key)
                break
            except Timeout as exc:
                record.notes.append(f"attempt {attempt}: {exc}")
        record.verification = self.verifier(self.network, record)
        record.trail_entry = self.trail.append({
            "event": "effect", "itinerary": p.itinerary, "amount_usd": p.amount_usd,
            "permission_id": record.permission.permission_id,
            "key": record.idempotency_key,
            "verified": record.verification["ok"]})
        missing = record.missing_after_effect(ACTOR)
        if missing:
            raise Refused(missing)
        return record


def naive_refund(network: CardNetwork, itinerary: str, amount_usd: float,
                 max_attempts: int = 3) -> list[str]:
    """The pilot as it ran: retry on timeout, no key, no permission record."""
    notes = []
    for attempt in range(1, max_attempts + 1):
        try:
            network.refund(itinerary, amount_usd, key=None)
            break
        except Timeout as exc:
            notes.append(f"attempt {attempt}: {exc}")
    return notes


def mint_key(record: ChainRecord) -> str:
    """Minted once by the control plane, before the first attempt, from the permission."""
    p, perm = record.proposal, record.permission
    raw = f"{p.action}|{p.itinerary}|{p.amount_usd:.2f}|{perm.permission_id}"
    return "idem-" + hashlib.sha256(raw.encode()).hexdigest()[:16]
