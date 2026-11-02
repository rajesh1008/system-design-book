"""Stand-ins for the systems the agent changes: the payment processor,
the airline reservation system, and the voucher ledger.

Each records every effect and whether the effect arrived through the
gateway. The systems cannot refuse an unmediated call (real ones cannot
tell either); they only remember it, so the path test can count it.
"""
from __future__ import annotations

import contextvars
from dataclasses import dataclass, field

# Set by the gateway for the length of one mediated call, and by nothing else.
MEDIATED: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "mediated", default=None)


class Bypass(Exception):
    """Raised by a strict world when an effect arrives outside the gateway."""


@dataclass
class World:
    strict: bool = False
    effects: list[dict] = field(default_factory=list)

    def _apply(self, system: str, kind: str, ref: str, usd: float,
               key: str | None) -> dict:
        via = MEDIATED.get()
        if via is None and self.strict:
            raise Bypass(f"{system}: {kind} {ref} outside the gateway")
        if key is not None:
            for e in self.effects:
                if e["system"] == system and e["key"] == key:
                    return dict(e, replayed=True)
        n = sum(1 for e in self.effects if e["system"] == system) + 1
        prefix = {"processor": "CR", "airline": "PNR", "vouchers": "VC"}[system]
        effect = {"id": f"{prefix}-{n:05d}", "system": system, "kind": kind,
                  "ref": ref, "usd": round(usd, 2), "key": key,
                  "mediated_by": via}
        self.effects.append(effect)
        return dict(effect, replayed=False)

    # The three systems of record, one call each.
    def refund(self, ref: str, usd: float, key: str | None = None) -> dict:
        return self._apply("processor", "refund", ref, usd, key)

    def rebook(self, ref: str, usd: float, key: str | None = None) -> dict:
        return self._apply("airline", "rebook", ref, usd, key)

    def voucher(self, ref: str, usd: float, key: str | None = None) -> dict:
        return self._apply("vouchers", "voucher", ref, usd, key)

    # What a verifier reads: the system's own record, not the actor's report.
    def records(self, system: str, ref: str) -> list[dict]:
        return [e for e in self.effects
                if e["system"] == system and e["ref"] == ref]

    def unmediated(self) -> list[dict]:
        return [e for e in self.effects if e["mediated_by"] is None]
