"""The tool refuses what the convention forbids (Chapter 12).

Chapter 7's executor keys every effect before its first attempt and
writes it to the ledger. That held for every path that used the
executor. It did not hold for a path that called the processor with
its own client and its own credential: the rule was a convention, and
nothing at the tool enforced it.

`GuardedClient` wraps a supplier endpoint and refuses a call unless:

    the tool is registered (it has a contract in corpus.tools)
    the caller holds the gateway's credential
    the call carries the ledger's reference, and the ledger shows that
        entry in the attempting state
    for a tool with native keys, the key sent is the ledger's key

A refusal raises `Refused` before the supplier is touched, so a refused
call is never an effect. The wrapper has the same surface as a
SupplierSim, so the Chapter 7 executor runs through it unchanged.

`writers_outside_gateway` is the credential inventory's question: which
credentials can write to a system of record and are not the gateway's.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from corpus.tools import NATIVE, TOOLS, SupplierSim
from .ledger import Ledger

GATEWAY = "gw-effects"
REGISTERED = {t.name for t in TOOLS}


class Refused(Exception):
    """The guarded tool would not apply this call."""


@dataclass
class GuardedClient:
    sim: SupplierSim
    ledger: Ledger
    credential: str = GATEWAY
    refusals: list[tuple[str, str]] = field(default_factory=list)

    # the SupplierSim surface the executor reads
    @property
    def tool(self):
        return self.sim.tool

    @property
    def support(self) -> str:
        return self.sim.support

    @property
    def faults(self) -> dict:
        return self.sim.faults

    @property
    def calls(self) -> int:
        return self.sim.calls

    def _refuse(self, ref: Optional[str], why: str) -> None:
        self.refusals.append((ref or "-", why))
        raise Refused(f"{self.sim.tool.name}: {why}")

    def check(self, key: Optional[str], ref: Optional[str]) -> None:
        if self.sim.tool.name not in REGISTERED:
            self._refuse(ref, "unregistered effect")
        if self.credential != GATEWAY:
            self._refuse(ref, f"credential {self.credential} may not "
                              "write")
        if ref is None or ref not in self.ledger.entries:
            self._refuse(ref, "no ledger entry")
        if self.ledger.entries[ref].state != "attempting":
            self._refuse(ref, f"entry is {self.ledger.entries[ref].state}")
        if self.sim.support == NATIVE and key != ref:
            self._refuse(ref, "unkeyed effect" if key is None
                         else "key is not the ledger's key")

    def call(self, request: dict, key: Optional[str] = None,
             ref: Optional[str] = None, at: float = 0.0,
             lag: float = 0.0) -> dict:
        self.check(key, ref)
        return self.sim.call(request, key=key, ref=ref, at=at, lag=lag)

    def lookup(self, ref: str, now: float):
        return self.sim.lookup(ref, now)


@dataclass(frozen=True)
class Credential:
    name: str
    holder: str
    writes: tuple[str, ...]      # systems of record it can change


def writers_outside_gateway(creds: list[Credential]) -> list[Credential]:
    """Every credential that can change a system of record and is not
    the gateway's. The answer the design wants is an empty list."""
    return [c for c in creds if c.writes and c.name != GATEWAY]
