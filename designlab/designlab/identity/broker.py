"""The secret broker: the only holder of system-of-record keys.

Each system of record takes one API key, as most do. The broker holds
it and fills it in on the way out, after checking that the run token
the gateway verified covers this tool and this itinerary. The model,
the harness, and the run never see a key. `scan_context` is the check
the context assembler runs before anything reaches the model: a held
key, a credential-shaped string, or a run token in the context is a
refusal, not a warning.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from common.rand import seeded
from common.redact import find_secrets

from .tokens import Claims

RUN_TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_\-]{40,}\.[A-Za-z0-9_\-]{43}")


@dataclass
class SystemOfRecord:
    """A system that knows one key and logs who it was told is acting."""
    name: str
    key: str
    log: list = field(default_factory=list)

    def request(self, key: str, on_behalf_of: str, tool: str) -> bool:
        if key != self.key:
            self.log.append(("rejected", on_behalf_of, tool))
            return False
        self.log.append(("ok", on_behalf_of, tool))
        return True


class BrokerRefused(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class SecretBroker:
    def __init__(self, systems: list[str], seed: int = 32):
        rng = seeded(seed, "identity", "broker")
        self._keys = {s: f"lab-sor-{s}-{rng.getrandbits(64):016x}"
                      for s in systems}
        self.sor = {s: SystemOfRecord(s, k) for s, k in self._keys.items()}
        self.fills = 0
        self.refusals: list[str] = []

    def fill(self, claims: Claims | None, system: str, tool: str,
             args: dict) -> None:
        """Present the key for this one request, or refuse."""
        if claims is None:
            return self._refuse("no_run_identity")
        if tool not in claims.tools:
            return self._refuse("not_in_run_scope")
        trip = args.get("itinerary_id", args.get("booking_ref"))
        if trip is not None and trip != claims.itinerary:
            return self._refuse("wrong_itinerary")
        if system not in self._keys:
            return self._refuse("no_key_held")
        self.fills += 1
        obo = f"{claims.run} for {claims.sub}"
        if not self.sor[system].request(self._keys[system], obo, tool):
            return self._refuse("key_rejected")

    def _refuse(self, reason: str) -> None:
        self.refusals.append(reason)
        raise BrokerRefused(reason)

    def scan_context(self, text: str) -> list[str]:
        """Empty when the text may go to the model."""
        found = [f"held key for {s}" for s, k in self._keys.items()
                 if k in text]
        found += find_secrets(text)
        if RUN_TOKEN_SHAPE.search(text):
            found.append("run token")
        return found

    def held(self) -> list[str]:
        return sorted(self._keys)


class BrokeredServer:
    """A tool server whose calls go out with a key the broker fills."""

    def __init__(self, inner, broker: SecretBroker, system: str):
        self.inner = inner
        self.broker = broker
        self.system = system
        self.claims: Claims | None = None

    def __getattr__(self, name):
        return getattr(self.inner, name)

    @property
    def requests(self) -> int:
        return self.inner.requests

    def handle(self, tool: str, args: dict) -> dict:
        self.broker.fill(self.claims, self.system, tool, args)
        return self.inner.handle(tool, args)
