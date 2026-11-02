"""The action plane: the agent loop and the one gateway to every tool.

The loop asks knowledge for context, turns the model's output into a
typed proposal, and sends it to control. It holds no tool client of its
own; each tool it can call is a GatewayTool. The gateway checks the chain
record, redeems the permission with control, and only then lets the
adapter touch a system of record.
"""
from __future__ import annotations

from dataclasses import dataclass

from chain.record import ChainRecord, Permission, Proposal, Refused

from .world import MEDIATED

ADAPTERS = {
    "refund": lambda world, r: world.refund(
        r.proposal.itinerary, r.proposal.amount_usd, r.idempotency_key),
    "rebook": lambda world, r: world.rebook(
        r.proposal.itinerary, r.proposal.amount_usd, r.idempotency_key),
    "voucher": lambda world, r: world.voucher(
        r.proposal.itinerary, r.proposal.amount_usd, r.idempotency_key),
}
SYSTEMS = {"refund": "processor", "rebook": "airline",
           "voucher": "vouchers"}


class Gateway:
    name = "gateway"

    def __init__(self, world, control, trail, actor: str = "agent-loop"):
        self.world, self.control, self.trail = world, control, trail
        self.actor = actor
        self.calls = 0

    def call(self, tool: str, record: ChainRecord) -> dict:
        missing = record.missing_before_effect(self.actor)
        if missing:
            raise Refused(missing)
        problems = self.control.redeem(record)
        if problems:
            raise Refused(problems)
        token = MEDIATED.set(self.name)
        try:
            effect = ADAPTERS[tool](self.world, record)
        finally:
            MEDIATED.reset(token)
        self.calls += 1
        record.execution = effect
        self.trail.effect(record, effect)
        return effect


class GatewayTool:
    """What the loop holds: a name bound to the gateway, nothing more."""

    def __init__(self, gateway: Gateway, tool: str):
        self.gateway, self.tool = gateway, tool
        self.system = SYSTEMS[tool]

    def __call__(self, record: ChainRecord) -> dict:
        return self.gateway.call(self.tool, record)


class FastPathRefund:
    """The injected failure: a refund tool holding its own processor client.

    It was added "for small refunds" and never passes the gateway, so no
    permission is redeemed and no effect line is written.
    """
    system = "processor"

    def __init__(self, world):
        self.world = world

    def __call__(self, record: ChainRecord) -> dict:
        p = record.proposal
        return self.world.refund(p.itinerary, p.amount_usd, None)


# What the customer may be told is read from the chain, not composed by
# the model. "done" exists only for a verified outcome.
CUSTOMER_STATES = ("received", "waiting for approval", "with a person",
                   "in progress", "done", "declined")


def customer_state(decision, record: ChainRecord | None,
                   queued: bool = False) -> str:
    if decision.verdict == "deny":
        return "declined"
    if decision.verdict == "escalate":
        if decision.reason == "approval required":
            return "waiting for approval"
        return "with a person"
    if record is None or record.execution is None:
        return "received"
    v = record.verification
    if v is not None and v["ok"] and v["verified_by"] != "agent-loop":
        return "done"
    return "in progress"


@dataclass
class Outcome:
    itinerary: str
    task: str
    level: str
    verdict: str
    handoff: str | None
    customer: str
    model_said: str          # what the model wanted to tell the customer
    path: str                # agent, assisted, or person
    waited_s: float = 0.0


class AgentLoop:
    name = "agent-loop"

    def __init__(self, knowledge, control, trail, tools: dict,
                 policy_in_loop: bool = False):
        self.knowledge, self.control, self.trail = knowledge, control, trail
        self.tools = tools
        self.policy_in_loop = policy_in_loop

    def propose(self, case) -> Proposal:
        # Stand-in for the model: its tool call, typed. No live API here.
        return Proposal(case["task"], case["itinerary"], case["usd"],
                        case.get("reason", "customer request"))

    def run(self, case, approvers) -> Outcome:
        ctx = self.knowledge.context(case["itinerary"])
        proposal = self.propose(case)
        model_said = "done"      # what an unconstrained model tends to say
        if self.policy_in_loop:
            return self._run_self_permitted(proposal, model_said)
        fast = self.tools.get(proposal.action + "_fast")
        if fast is not None and proposal.amount_usd <= 200:
            # The model sees a tool described "for small refunds" and uses
            # it. No decision, no permission, no trail line.
            fast(ChainRecord(proposal=proposal))
            return Outcome(proposal.itinerary, proposal.action, "none",
                           "none", None, "in progress", model_said,
                           "unknown")
        d = self.control.decide(proposal, ctx)
        waited, queued = 0.0, False
        if d.verdict == "escalate" and d.reason == "approval required":
            row = self.control.autonomy.row(proposal.action)
            delay = case["approver_s"]
            if delay <= row.sync_wait_s:
                waited = delay
                d = self.control.approve(d.pending_id, approvers.pick(case))
            else:
                waited, queued = row.sync_wait_s, True
        record = None
        if d.verdict == "permit":
            record = ChainRecord(proposal=proposal, permission=d.permission,
                                 idempotency_key=d.key)
            self.tools[proposal.action](record)
            if case.get("lost"):
                # The system of record dropped the effect after replying.
                self.trail.world.effects.pop()
            self.trail.verify(record)
        state = customer_state(d, record, queued)
        level = d.level
        if d.verdict != "permit":
            path = "person"
        elif d.permission.granted_by == "policy-engine":
            path = "agent" if state == "done" else "person"
        else:
            path = "assisted"
        # Sync: a person answered while the customer waited. Async: the
        # case went to a queue with a promised time.
        handoff = "sync" if waited and not queued else None
        if queued or d.verdict == "escalate" or state == "in progress":
            handoff = "async"
        return Outcome(proposal.itinerary, proposal.action, level,
                       d.verdict, handoff, state, model_said, path, waited)

    def _run_self_permitted(self, proposal, model_said) -> Outcome:
        # The anti-pattern: the loop evaluates policy and signs for itself.
        perm = Permission("PRM-LOOP", self.name, "refunds-v3", 1500.0)
        record = ChainRecord(proposal=proposal, permission=perm,
                             idempotency_key="self-minted")
        try:
            self.tools[proposal.action](record)
            verdict = "permit"
        except Refused as r:
            verdict = "refused: " + ", ".join(r.missing)
        return Outcome(proposal.itinerary, proposal.action, "self", verdict,
                       None, "received", model_said, "person")
