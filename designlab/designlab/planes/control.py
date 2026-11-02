"""The control plane: policy, permission, approval, and budgets.

It runs outside the agent loop and is the only component that issues a
permission or mints an idempotency key.

Contract C2 (action to control): a typed proposal goes in; one decision
comes out, permit, escalate, or deny, with a reason and a decision record.
Contract C3 (control to gateway): the gateway redeems a permission before
any effect; control accepts only a permission it issued, for the same
proposal and the same key, and refuses everything else.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from chain.record import Permission, Proposal

ENGINE = "policy-engine"


def proposal_hash(p: Proposal) -> str:
    body = json.dumps([p.action, p.itinerary, round(p.amount_usd, 2)])
    return hashlib.sha256(body.encode()).hexdigest()[:16]


@dataclass
class Decision:
    verdict: str                      # permit, escalate, deny
    task: str
    level: str
    reason: str
    permission: Permission | None = None
    key: str | None = None
    handoff: str | None = None        # sync, async, or None
    receiver: str | None = None
    pending_id: str | None = None


@dataclass
class _Issued:
    permission: Permission
    phash: str
    key: str
    uses: int = 0


@dataclass
class ControlPlane:
    autonomy: "object"                # AutonomyTable
    trail: "object"                   # TrailPlane
    agent_identity: str = "agent-loop"
    issued: dict[str, _Issued] = field(default_factory=dict)
    pending: dict[str, tuple[Proposal, Decision]] = field(default_factory=dict)
    spent_usd: dict[str, float] = field(default_factory=dict)

    # C2: decide on a proposal --------------------------------------------
    def decide(self, proposal: Proposal, context) -> Decision:
        row = self.autonomy.row(proposal.action)
        d = Decision("deny", proposal.action, row.level, "")
        if row.level == "suggest":
            d.verdict, d.reason = "escalate", "level is suggest"
        elif context.stale:
            d.verdict = "escalate"
            d.reason = "stale fact: " + ",".join(context.stale)
        elif proposal.amount_usd > row.limit_usd:
            d.verdict, d.reason = "escalate", "over the task limit"
        elif self._over_budget(row, proposal.amount_usd):
            d.verdict, d.reason = "escalate", "daily budget reached"
        elif row.level == "act_with_approval":
            d.verdict, d.reason = "escalate", "approval required"
        else:
            d.verdict, d.reason = "permit", f"{row.policy} within limit"
        if d.verdict == "escalate":
            d.handoff, d.receiver = row.handoff, row.receiver
            d.pending_id = f"APR-{len(self.pending) + 1:05d}"
            self.pending[d.pending_id] = (proposal, d)
        else:
            self._issue(d, proposal, ENGINE, row)
        self.trail.decision(d, proposal)
        return d

    def approve(self, pending_id: str, approver: str) -> Decision:
        proposal, prior = self.pending.pop(pending_id)
        row = self.autonomy.row(proposal.action)
        d = Decision("deny", prior.task, prior.level, "", handoff=prior.handoff,
                     receiver=prior.receiver, pending_id=pending_id)
        if approver == self.agent_identity:
            d.reason = "approver is the agent"
        else:
            d.verdict, d.reason = "permit", f"approved by {approver}"
            self._issue(d, proposal, approver, row)
        self.trail.decision(d, proposal)
        return d

    def new_day(self) -> None:
        self.spent_usd.clear()

    def _over_budget(self, row, usd: float) -> bool:
        if row.daily_budget_usd is None:
            return False
        return self.spent_usd.get(row.task, 0.0) + usd > row.daily_budget_usd

    def _issue(self, d: Decision, p: Proposal, grantor: str, row) -> None:
        pid = f"PRM-{len(self.issued) + 1:05d}"
        cap = min(row.limit_usd, row.policy_cap_usd)
        perm = Permission(pid, grantor, row.policy, cap)
        key = hashlib.sha256(f"{pid}:{proposal_hash(p)}".encode()
                             ).hexdigest()[:20]
        self.issued[pid] = _Issued(perm, proposal_hash(p), key)
        d.permission, d.key = perm, key

    # C3: redeem at the gateway -------------------------------------------
    def redeem(self, record) -> list[str]:
        perm = record.permission
        got = self.issued.get(perm.permission_id) if perm else None
        if got is None:
            return ["permission not issued by control"]
        problems = []
        if got.permission != perm:
            problems.append("permission altered after issue")
        if got.phash != proposal_hash(record.proposal):
            problems.append("permission is for another proposal")
        if got.key != record.idempotency_key:
            problems.append("key not minted for this permission")
        if not problems:
            if got.uses == 0:
                task = record.proposal.action
                self.spent_usd[task] = (self.spent_usd.get(task, 0.0)
                                        + record.proposal.amount_usd)
            got.uses += 1
        return problems
