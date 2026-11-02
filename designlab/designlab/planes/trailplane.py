"""The trail plane: decision records, effect records, and verification.

Contract C4 (action to trail): every effect writes one line naming the
permission, the key, and the system's own reference.
Contract C5 (control to trail): every decision writes one line, including
the ones that refused or escalated.
Contract C6 (trail to everyone): an outcome counts as verified only when
a reader that did not act finds exactly one matching effect in the system
of record.
"""
from __future__ import annotations

from common.trail import TrailWriter, check_trail

SYSTEM_FOR = {"refund": "processor", "rebook": "airline",
              "voucher": "vouchers"}
VERIFIERS = {"processor": "settlement-reconciler",
             "airline": "pnr-reconciler", "vouchers": "voucher-reconciler"}


class TrailPlane:
    def __init__(self, world, clock):
        self.world = world
        self.writer = TrailWriter(clock=clock)

    def decision(self, d, proposal) -> None:
        self.writer.append({
            "kind": "decision", "task": d.task, "level": d.level,
            "verdict": d.verdict, "reason": d.reason,
            "itinerary": proposal.itinerary,
            "usd": round(proposal.amount_usd, 2),
            "permission": d.permission.permission_id if d.permission
            else None,
            "granted_by": d.permission.granted_by if d.permission else None,
            "handoff": d.handoff, "pending": d.pending_id})

    def effect(self, record, effect: dict) -> None:
        record.trail_entry = self.writer.append({
            "kind": "effect", "task": record.proposal.action,
            "itinerary": record.proposal.itinerary,
            "permission": record.permission.permission_id,
            "key": record.idempotency_key, "ref": effect["id"],
            "replayed": effect.get("replayed", False)})

    def verify(self, record) -> dict:
        system = SYSTEM_FOR[record.proposal.action]
        found = [e for e in self.world.records(system,
                                               record.proposal.itinerary)
                 if e["key"] == record.idempotency_key]
        ok = (len(found) == 1
              and abs(found[0]["usd"] - record.proposal.amount_usd) < 0.005)
        v = {"verified_by": VERIFIERS[system], "system": system,
             "matches": len(found), "ok": ok}
        record.verification = v
        self.writer.append({"kind": "verification",
                            "itinerary": record.proposal.itinerary,
                            "key": record.idempotency_key, **v})
        return v

    def intact(self) -> bool:
        return check_trail(self.writer.lines) == []

    def count(self, kind: str) -> int:
        return sum(1 for line in self.writer.lines
                   if f'"kind": "{kind}"' in line)
