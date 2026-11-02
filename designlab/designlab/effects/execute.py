"""The executor: one effect, every attempt through the ledger (Section 3).

On a timeout the outcome is unknown. What happens next depends on the
tool's contract, never on the model:

    native   retry with the same key; the supplier replays its receipt
    lookup   ask the supplier at 5, 15 and 30 seconds and at its
             documented visibility bound; found means committed, still
             absent at the bound means the request never landed, so
             attempt again under the same key
    none     do not retry; escalate to a person (money, inventory) or
             abandon (messages, where a miss is cheaper than a repeat)

`unkeyed()` is the pilot's shape for comparison: the framework retries
the call after a timeout and nothing remembers the first attempt.
"""
from __future__ import annotations

from typing import Callable, Optional

from corpus.tools import (KeyConflict, LOOKUP, NATIVE, SupplierSim,
                          SupplierTimeout)
from .keys import EffectKey
from .ledger import Entry, Ledger

LOOKUP_AT = (5.0, 15.0, 30.0)
TIMEOUT_S = 8.0
LATENCY_S = 1.2
KEY_RETENTION_S = 24 * 3600   # what one processor documents; [VERIFY]

Faults = Callable[[str], str]   # tool name -> "", "late" or "lost"
Lags = Callable[[str], float]   # tool name -> seconds until visible


def no_faults(_: str) -> str:
    return ""


def no_lag(_: str) -> float:
    return 0.0


class Executor:
    def __init__(self, ledger: Ledger, sims: dict[str, SupplierSim],
                 faults: Faults = no_faults, lags: Lags = no_lag,
                 max_attempts: int = 3, holder: str = "action-executor"):
        self.ledger, self.sims = ledger, sims
        self.faults, self.lags = faults, lags
        self.max_attempts, self.holder = max_attempts, holder
        self.now = 0.0
        self.calls = 0

    def _call(self, sim: SupplierSim, request: dict,
              key: Optional[str], ref: Optional[str]) -> dict:
        self.calls += 1
        fault = self.faults(sim.tool.name)
        if fault:
            sim.faults[sim.calls + 1] = fault
        at = self.now
        try:
            out = sim.call(request, key=key, ref=ref, at=at,
                           lag=self.lags(sim.tool.name))
        except SupplierTimeout:
            self.now = at + TIMEOUT_S
            raise
        self.now = at + LATENCY_S
        return out

    def run(self, ek: EffectKey, request: dict) -> Entry:
        e, new = self.ledger.reserve(ek, self.now)
        if not new and e.state == "committed":
            return e   # stored receipt; the tool is not called again
        if not new:
            raise ValueError(f"{ek.key} is {e.state}; resolve it first")
        sim = self.sims[ek.tool]
        key = ek.key
        while True:
            if e.attempts >= self.max_attempts:
                self.ledger.move(key, "escalated", self.now,
                                 "attempts used up")
                return e
            token = self.ledger.acquire(key, self.holder, self.now)
            self.ledger.move(key, "attempting", self.now,
                             f"attempt {e.attempts + 1}", token)
            send_key = key if sim.support == NATIVE else None
            try:
                receipt = self._call(sim, request, send_key, key)
            except KeyConflict as err:
                self.ledger.move(key, "failed", self.now, str(err), token)
                return e
            except SupplierTimeout:
                self.ledger.move(key, "unknown", self.now, "timeout", token)
                if not self._resolve(e, sim, token):
                    return e
                if e.state == "committed":
                    return e
                continue   # back to attempting under the same key
            if receipt.get("status") == "refused":
                self.ledger.move(key, "failed", self.now, "refused", token)
                return e
            e.receipt = receipt
            self.ledger.move(key, "committed", self.now,
                             receipt["effect_id"] or "nothing left", token)
            return e

    def _resolve(self, e: Entry, sim: SupplierSim, token: int) -> bool:
        """Leave the unknown state. True means try again."""
        key = e.key.key
        age = self.now - e.key.minted_at
        if sim.support == NATIVE and age < KEY_RETENTION_S:
            self.now += 1.0
            return True   # next attempt replays the key
        if sim.support == LOOKUP:
            start = self.now
            bound = float(sim.tool.visible_within_s)
            for offset in sorted({*LOOKUP_AT, bound}):
                if offset > bound:
                    break
                self.now = start + offset
                found = sim.lookup(key, self.now)
                if found:
                    e.receipt = dict(found, replayed=False)
                    self.ledger.move(key, "committed", self.now,
                                     f"lookup at +{offset:.0f}s", token)
                    return False
            return True   # absent past the bound: it never landed
        if sim.tool.supplier == "message":
            self.ledger.move(key, "abandoned", self.now,
                             "at most once: not resent", token)
            return False
        self.ledger.move(key, "escalated", self.now,
                         "no key, no lookup: to a person", token)
        return False


def unkeyed(sim: SupplierSim, request: dict, faults: Faults = no_faults,
            retries: int = 2) -> int:
    """The pilot's shape: retry on timeout, no key, no memory.
    Returns the number of calls made."""
    calls = 0
    for _ in range(1 + retries):
        calls += 1
        fault = faults(sim.tool.name)
        if fault:
            sim.faults[sim.calls + 1] = fault
        try:
            sim.call(request)
            return calls
        except SupplierTimeout:
            continue
    return calls
