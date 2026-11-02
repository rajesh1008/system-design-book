"""The policy engine: the decision point; the gateway enforces.

The engine reads four things: the caller's identity, the tool, the
arguments, and its own history. It has no field for the conversation,
so a claim made in the conversation cannot reach a rule. Every
decision names the rule, the policy version, the bundle, and the
bundle's digest, and goes to the trail as one line.

Verdicts:
  permit    a permission is issued, bound to the argument digest
  approve   a person must decide; a card is filed
  route     not an agent action; the case goes to the named desk
  deny      refused; the reason says why
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from gateway.core import Policy
from toolargs.layer import digest

from . import temporal
from .approval import ApprovalGate
from .budgets import EffectBudgets
from .bundle import BundleStore
from .tiers import tier_of

ENGINE = "policy-engine"
DEFAULT_VALID_MIN = 15


class EngineDown(Exception):
    pass


@dataclass(frozen=True)
class Request:
    caller: str
    tool: str
    kind: str
    args: dict
    session: str
    traveler: str = ""


@dataclass
class Decision:
    decision_id: str
    at: str
    verdict: str
    reason: str
    rule: str
    policy: str
    bundle: str
    bundle_digest: str
    tier: str
    digest: str
    permission: str = ""
    card: str = ""
    route: str = ""
    shadow: str = ""
    tool: str = ""
    amount: str = ""


@dataclass
class Grant:
    tool: str
    digest: str
    policy: str
    bundle: str
    granted_by: str
    expires: datetime
    card: str = ""


class EnginePolicy(Policy):
    """The gateway's permission check, backed by the engine's grants.

    Refuses a permission that is unknown, spent, for other arguments,
    granted by the agent, expired, or under a revoked version.
    """

    def __init__(self, engine: "PolicyEngine"):
        super().__init__()
        self.engine = engine
        self.grants: dict[str, Grant] = {}
        self.last = ""

    def grant(self, pid: str, g: Grant) -> None:
        self.grants[pid] = g
        self.issued[pid] = (g.tool, g.digest)

    def allows(self, permission, tool, args) -> bool:
        g = self.grants.get(permission or "")
        now = self.engine.clock.now()
        self.last = refusal(g, permission, tool, args, now,
                            self.spent, self.engine.bundles)
        if self.last:
            return False
        self.spent.add(permission)
        self.engine.spent(permission, g, tool, args, now)
        return True


def refusal(g, permission, tool, args, now, spent, bundles) -> str:
    if g is None:
        return "no_permission"
    if permission in spent:
        return "permission_spent"
    if (g.tool, g.digest) != (tool, digest(tool, args)):
        return "other_arguments"
    if g.granted_by.startswith("agent:"):
        return "granted_inside_loop"
    if now > g.expires:
        return "permission_expired"
    if g.policy in bundles.revoked_versions:
        return "version_revoked"
    return ""


@dataclass
class PolicyEngine:
    bundles: BundleStore
    approvals: ApprovalGate
    trail: object
    clock: object
    history: temporal.History = field(default_factory=temporal.History)
    budgets: EffectBudgets = field(default_factory=EffectBudgets)
    up: bool = True
    n: int = 0
    decisions: list[Decision] = field(default_factory=list)

    def __post_init__(self):
        self.policy = EnginePolicy(self)

    # -- deciding -------------------------------------------------------
    def decide(self, req: Request) -> Decision:
        if not self.up:
            raise EngineDown("policy engine unavailable")
        b = self.bundles.active()
        now = self.clock.now()
        self.n += 1
        d = self._evaluate(b, req, now, live=True)
        d.decision_id = f"pd-{self.n:05d}"
        sh = self.bundles.shadow()
        if sh is not None:
            d.shadow = self._evaluate(sh, req, now, live=False).verdict
        if req.kind == "read" and d.verdict == "permit":
            self.history.note(now, req.tool, req.args.get(
                "booking_ref", req.args.get("doc_id", "")), req.session)
        self.decisions.append(d)
        self.trail.append({"event": "policy_decision",
                           **{k: v for k, v in d.__dict__.items()
                              if v != ""}})
        return d

    def _evaluate(self, b, req: Request, now: datetime,
                  live: bool) -> Decision:
        dg = digest(req.tool, req.args)
        tier = tier_of(req.tool, req.kind)

        def out(verdict, reason, rule=None, **kw) -> Decision:
            return Decision("", now.isoformat(timespec="seconds"),
                            verdict, reason, rule["id"] if rule else "",
                            rule["policy"] if rule else "", b.revision,
                            b.digest, tier, dg, tool=req.tool,
                            amount=req.args.get("amount_usd", ""), **kw)

        rules = [r for r in b.rules if req.tool in r.get("tools", [])]
        if req.kind == "handoff":
            return out("permit", "handoff")
        if req.kind == "read":
            read = next((r for r in rules if r["type"] == "read"), None)
            if read is None:
                return out("permit", "read_not_in_bundle")
            return out("permit", "read", read)
        if not rules:
            return out("deny", "no_rule")
        if tier == "person":
            return out("route", "suggest_only", route="agent desk")
        needs_approval, why_rule = tier == "high", None
        for r in rules:
            t = r["type"]
            if t == "limit" and float(req.args.get(r["field"], 0)) \
                    > r["max"]:
                return out("route", "over_policy_limit", r,
                           route=r["route"])
            if t in ("count_within", "quiet_after", "escalate_after"):
                why = temporal.check(r, req.tool, req.args, req.session,
                                     now, self.history)
                if why == "untrusted_input_in_session":
                    needs_approval, why_rule = True, r
                elif why:
                    return out("route", why, r, route=r["route"])
        valid = next((r["minutes"] for r in b.rules
                      if r["type"] == "valid_for"), DEFAULT_VALID_MIN)
        allow = next((r for r in rules if r["type"] in
                      ("allow", "approval")), None)
        if allow is None:
            return out("deny", "no_allow_rule")
        card = None
        if needs_approval:
            rule = why_rule or allow
            card = self.approvals.approved_for(dg, now)
            if card is None:
                if not live:
                    return out("approve", "approval_needed", rule)
                c = self.approvals.file(req.tool, req.args, dg,
                                        req.caller, rule["id"])
                return out("approve", "approval_needed", rule,
                           card=c.card_id)
        if not live:
            return out("permit", "within_policy", allow)
        pid = f"pm-{self.n:05d}"
        budget = next((r for r in rules if r["type"] == "budget"), None)
        if budget is not None:
            stop = self.budgets.reserve(
                pid, req.caller, req.traveler or req.args.get(
                    "itinerary_id", ""), now.date().isoformat(),
                float(req.args[budget["field"]]))
            if stop:
                return out("route", f"budget_{stop}", budget,
                           route="agent desk")
        g = Grant(req.tool, dg, allow["policy"], b.revision, ENGINE,
                  now + timedelta(minutes=valid),
                  card.card_id if card else "")
        if card is not None:
            self.approvals.spend(card)
        self.policy.grant(pid, g)
        return out("permit", "approved" if card else "within_policy",
                   allow, permission=pid,
                   card=card.card_id if card else "")

    # -- what happened --------------------------------------------------
    def spent(self, pid: str, g: Grant, tool: str, args: dict,
              now: datetime) -> None:
        for k in ("itinerary_id", "ticket_number"):
            if k in args:
                self.history.note(now, tool, args[k])
        self.budgets.settle(pid, spent=True)

    def event(self, kind: str, key: str) -> None:
        """A system-of-record event, such as a fare change."""
        self.history.note(self.clock.now(), kind, key)
