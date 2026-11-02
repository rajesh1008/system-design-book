"""Eighteen supplier tool simulators with their idempotency contracts (Chapter 7).

Each tool is one write a Lakeshore action can cause at a supplier: an
airline, a hotel, a car-rental network, the payment processor, the
voucher ledger, or a customer message. Its contract says what the far
end does with a retry:

    native   the supplier stores the first result under our key and
             returns it to any retry with the same key; a different
             request under the same key is refused as a conflict
    lookup   no key, but the supplier can be asked whether a request
             carrying our reference exists; the answer is only
             reliable after `visible_within_s` seconds
    none     no key and no lookup; a retry is a second request

`SupplierSim` applies requests to an in-memory record that only the
supplier writes (its reservation history, folio, or settlement file).
Faults are injected per call: "late" applies the effect and loses the
answer, "lost" loses the request before anything happens. Both look the
same to the caller: a timeout.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional

NATIVE, LOOKUP, NONE = "native", "lookup", "none"
SUPPORT = (NATIVE, LOOKUP, NONE)


class SupplierTimeout(Exception):
    """The caller stopped waiting. The effect may or may not exist."""


class KeyConflict(Exception):
    """Same key, different request: the supplier refuses it."""


@dataclass(frozen=True)
class ToolSpec:
    name: str
    supplier: str          # airline, hotel, car, payment, ledger, message
    effect: str            # what one successful call does
    support: str           # native, lookup, none
    compensation: str      # the call that undoes it, or "" if none
    visible_within_s: int  # lookup tools: documented bound on visibility
    relative: bool = False  # True if a repeat acts on the next item

    def __post_init__(self):
        if self.support not in SUPPORT:
            raise ValueError(f"{self.name}: unknown support {self.support}")


TOOLS: tuple[ToolSpec, ...] = (
    # airlines and the global distribution system
    ToolSpec("airline-rebook-a", "airline", "reissue ticket on new flight",
             NATIVE, "airline-void-ticket", 0),
    ToolSpec("airline-rebook-b", "airline", "reissue ticket on new flight",
             LOOKUP, "airline-void-ticket", 40),
    ToolSpec("gds-reissue", "airline", "reissue ticket through the GDS",
             LOOKUP, "airline-void-ticket", 45),
    ToolSpec("airline-void-ticket", "airline", "void a ticket same day",
             LOOKUP, "", 30),
    ToolSpec("airline-seat-hold", "airline", "hold a seat for 20 minutes",
             NATIVE, "airline-release-hold", 0),
    ToolSpec("airline-cancel-segment", "airline", "cancel a booked segment",
             LOOKUP, "", 40),
    # hotels
    ToolSpec("hotel-cancel-channel", "hotel", "cancel a reservation",
             NATIVE, "", 0),
    ToolSpec("hotel-cancel-aggregator", "hotel", "cancel a reservation",
             LOOKUP, "", 45),
    ToolSpec("hotel-cancel-direct", "hotel", "cancel one room",
             NONE, "", 0, relative=True),
    ToolSpec("hotel-modify", "hotel", "change stay dates",
             LOOKUP, "hotel-modify", 45),
    ToolSpec("hotel-book", "hotel", "book a room",
             NATIVE, "hotel-cancel-channel", 0),
    # car rental
    ToolSpec("car-cancel", "car", "cancel a rental",
             LOOKUP, "", 20),
    ToolSpec("car-book", "car", "book a rental",
             NATIVE, "car-cancel", 0),
    # money
    ToolSpec("processor-refund", "payment", "refund to the card",
             NATIVE, "", 0),
    ToolSpec("fare-charge", "payment", "charge a fare difference",
             NATIVE, "processor-refund", 0),
    ToolSpec("voucher-ledger", "ledger", "issue a travel credit",
             NONE, "voucher-ledger-void", 0),
    # messages
    ToolSpec("customer-email", "message", "send an email",
             NONE, "", 0),
    ToolSpec("customer-sms", "message", "send a text message",
             NONE, "", 0),
)

BY_NAME = {t.name: t for t in TOOLS}


def spec(name: str) -> ToolSpec:
    return BY_NAME[name]


def fingerprint(request: dict) -> str:
    """Hash of the request's business fields, in a stable order."""
    raw = json.dumps(request, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass
class SupplierSim:
    """One supplier endpoint. Only this object writes `records`."""
    tool: ToolSpec
    faults: dict[int, str] = field(default_factory=dict)  # call -> fault
    honor_keys: Optional[bool] = None   # override the contract (labs)
    records: list[dict] = field(default_factory=list)
    _by_key: dict[str, tuple[str, dict]] = field(default_factory=dict)
    _items: dict[str, int] = field(default_factory=dict)  # relative ops
    calls: int = 0

    @property
    def support(self) -> str:
        if self.honor_keys is None:
            return self.tool.support
        return NATIVE if self.honor_keys else NONE

    def stock(self, target: str, items: int) -> None:
        """Give a target several items, e.g. two rooms on one booking."""
        self._items[target] = items

    def call(self, request: dict, key: Optional[str] = None,
             ref: Optional[str] = None, at: float = 0.0,
             lag: float = 0.0) -> dict:
        """Apply one request at time `at`. `key` is honored only if the
        contract has keys; `ref` is our reference, stored on the record
        for lookups; `lag` is how long the record takes to show up in a
        lookup (at most the tool's visible_within_s)."""
        self.calls += 1
        fault = self.faults.get(self.calls, "")
        if fault == "lost":
            raise SupplierTimeout(f"{self.tool.name}: no answer (call "
                                  f"{self.calls}, request lost)")
        fp = fingerprint(request)
        if self.support == NATIVE and key is not None:
            if key in self._by_key:
                old_fp, receipt = self._by_key[key]
                if old_fp != fp:
                    raise KeyConflict(f"{self.tool.name}: key reused "
                                      f"for a different request")
                if fault == "late":
                    raise SupplierTimeout(f"{self.tool.name}: no answer")
                return dict(receipt, replayed=True)
        receipt = self._apply(request, ref, at, lag)
        if self.support == NATIVE and key is not None:
            self._by_key[key] = (fp, receipt)
        if fault == "late":
            raise SupplierTimeout(f"{self.tool.name}: no answer (call "
                                  f"{self.calls}, applied)")
        return dict(receipt, replayed=False)

    def _apply(self, request: dict, ref: Optional[str], at: float,
               lag: float) -> dict:
        target = request["target"]
        item = None
        if self.tool.relative:
            left = self._items.get(target, 1)
            if left <= 0:
                return {"effect_id": None, "target": target,
                        "status": "nothing left"}
            item = self._items.get(target, 1) - left + 1
            self._items[target] = left - 1
        effect_id = f"{self.tool.supplier[:3].upper()}-" \
                    f"{len(self.records) + 1:05d}"
        rec = {"effect_id": effect_id, "tool": self.tool.name,
               "target": target, "request": request, "ref": ref, "at": at,
               "visible_at": at + min(lag, self.tool.visible_within_s)}
        if item is not None:
            rec["item"] = item
        self.records.append(rec)
        return {"effect_id": effect_id, "target": target, "status": "ok"}

    def lookup(self, ref: str, now: float) -> Optional[dict]:
        """Find a record carrying `ref`, if it is visible at `now`."""
        if self.support != LOOKUP:
            raise NotImplementedError(f"{self.tool.name} has no lookup")
        for rec in self.records:
            if rec["ref"] == ref and now >= rec["visible_at"]:
                return {"effect_id": rec["effect_id"],
                        "target": rec["target"], "status": "ok"}
        return None

    def effects_for(self, target: str) -> list[dict]:
        """The supplier's own record for one target: the second witness."""
        return [r for r in self.records if r["target"] == target]


def counts() -> dict[str, dict[str, int]]:
    """Tools by supplier type and contract, for the support table."""
    out: dict[str, dict[str, int]] = {}
    for t in TOOLS:
        row = out.setdefault(t.supplier, {s: 0 for s in SUPPORT})
        row[t.support] += 1
    return out
