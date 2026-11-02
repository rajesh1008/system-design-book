"""The chain record: the evidence one effect must carry (Chapter 2).

Six fields, filled in order by different components:

    proposal         what the model asked for (written by the loop from model output)
    permission       who or what allowed it, under which policy (written outside the loop)
    idempotency_key  minted once by the control plane, before the first attempt
    execution        what the tool reported, against that key
    verification     what a component that did not act found in the world
    trail_entry      the append-only line that ties the other five together
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


class Refused(Exception):
    """Raised when an effect is attempted without the evidence it needs."""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("refused: missing " + ", ".join(missing))


@dataclass(frozen=True)
class Proposal:
    action: str          # e.g. "refund"
    itinerary: str       # Lakeshore itinerary reference
    amount_usd: float
    reason: str          # the model's stated reason, kept verbatim


@dataclass(frozen=True)
class Permission:
    permission_id: str
    granted_by: str      # a policy engine or a named approver, never the agent
    policy_version: str
    max_amount_usd: float


@dataclass
class ChainRecord:
    proposal: Optional[Proposal] = None
    permission: Optional[Permission] = None
    idempotency_key: Optional[str] = None
    execution: Optional[dict] = None
    verification: Optional[dict] = None
    trail_entry: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def missing_before_effect(self, actor: str) -> list[str]:
        """Evidence that must exist before any effect is attempted."""
        missing = [name for name in ("proposal", "permission", "idempotency_key")
                   if getattr(self, name) is None]
        p = self.permission
        if p is not None and p.granted_by == actor:
            missing.append("permission granted outside the loop")
        if p is not None and self.proposal is not None \
                and self.proposal.amount_usd > p.max_amount_usd:
            missing.append("permission covering this amount")
        return missing

    def missing_after_effect(self, actor: str) -> list[str]:
        """Evidence that must exist before an effect counts as done."""
        missing = [name for name in ("execution", "verification", "trail_entry")
                   if getattr(self, name) is None]
        v = self.verification
        if v is not None and v.get("verified_by") == actor:
            missing.append("verification by a component that did not act")
        return missing
