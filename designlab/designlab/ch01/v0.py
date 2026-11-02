"""designlab v0: one request, one action, six trail lines (Chapter 1).

The pieces, in the order a request meets them:

    classify_output  is the model output an answer or a proposed action
    PolicyEngine     grants or denies a permission, outside the loop
    V0Loop.execute   refuses without a permission, acts once under a key
    reconcile        a component that did not act checks the effect
    trail            one append-only, hash-linked line per step

`demo_shape` is the October 6 demo for contrast: the model's tool call
goes straight to the tool, with no permission and no key.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Optional

from chain.record import ChainRecord, Permission, Proposal, Refused
from common.trail import TrailWriter

ACTOR = "action-executor"
VERIFIER = "settlement-reconciler"
POLICY = "policy-engine"

# What each action does to the world, and the limit the policy allows
# without a person. Refund and rebook limits are the pilot's; the hotel
# limit is a lab value for the Try It Yourself exercise.
ACTIONS = {
    "refund": {"effect": "credit to card", "limit": 1500.00,
               "policy": "refunds-v3"},
    "rebook": {"effect": "ticket reissued", "limit": 1500.00,
               "policy": "changes-v1"},
    "hotel_cancel": {"effect": "booking canceled", "limit": 800.00,
                     "policy": "hotels-v1"},
}


class Timeout(Exception):
    """The caller stopped waiting. The effect may or may not exist."""


# ------------------------------------------------------------ the world
@dataclass
class Network:
    """A stand-in for the card network, airline or hotel system.

    `slow_calls` holds 1-based call numbers whose effect is applied but
    whose answer arrives after the caller's 8.0 s timeout.
    """
    slow_calls: set[int] = field(default_factory=set)
    honor_keys: bool = True
    effects: list[dict] = field(default_factory=list)
    calls: int = 0
    _by_key: dict[str, dict] = field(default_factory=dict)

    def apply(self, action: str, ref: str, amount_usd: float,
              key: Optional[str]) -> dict:
        self.calls += 1
        if self.honor_keys and key is not None and key in self._by_key:
            return dict(self._by_key[key], replayed=True, status=200)
        effect = {"effect_id": f"EF-{len(self.effects) + 1:05d}",
                  "action": action, "ref": ref, "amount_usd": amount_usd}
        self.effects.append(effect)
        if key is not None:
            self._by_key[key] = effect
        if self.calls in self.slow_calls:
            raise Timeout(f"no answer after 8.0 s (call {self.calls})")
        return dict(effect, replayed=False, status=200)

    def found(self, action: str, ref: str) -> list[dict]:
        """What the settlement side of the world shows for one ref."""
        return [e for e in self.effects
                if e["ref"] == ref and e["action"] == action]


# ------------------------------------------------- output and proposal
def classify_output(text: str) -> tuple[str, Optional[Proposal]]:
    """Step 1 of the procedure: is this output an answer or an action?

    An output is an action only when it parses into a known action with
    a reference and an amount. Anything else is an answer: words for a
    person to read, with no effect on the world.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return "answer", None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return "answer", None
    action = data.get("action")
    ref = data.get("itinerary") or data.get("ref")
    amount = data.get("amount_usd")
    if action not in ACTIONS or not ref or not isinstance(
            amount, (int, float)):
        return "answer", None
    return "action", Proposal(action, str(ref), round(float(amount), 2),
                              str(data.get("reason", ""))[:80])


# ------------------------------------------------------------- policy
@dataclass
class PolicyEngine:
    """Grants or denies, outside the loop. Its ids are sequential."""
    issued: int = 0
    first_id: int = 20931

    def decide(self, p: Proposal) -> Optional[Permission]:
        rule = ACTIONS[p.action]
        if p.amount_usd > rule["limit"]:
            return None                  # a person decides instead
        pid = f"PRM-{self.first_id + self.issued}"
        self.issued += 1
        return Permission(pid, granted_by=POLICY,
                          policy_version=rule["policy"],
                          max_amount_usd=rule["limit"])


def mint_key(p: Proposal, perm: Permission) -> str:
    """Minted once, from the permission, before the first attempt."""
    raw = f"{p.action}|{p.itinerary}|{p.amount_usd:.2f}|" \
          f"{perm.permission_id}"
    return "idem-" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def reconcile(world: Network, p: Proposal) -> dict:
    """Verify against the world's own record, not the executor's."""
    found = world.found(p.action, p.itinerary)
    ok = len(found) == 1 and found[0]["amount_usd"] == p.amount_usd
    return {"verified_by": VERIFIER, "found": len(found), "ok": ok}


# --------------------------------------------------------------- loop
@dataclass
class V0Loop:
    world: Network
    trail: TrailWriter
    policy: PolicyEngine = field(default_factory=PolicyEngine)
    check_permission: bool = True        # Try It Yourself: set False
    max_attempts: int = 3

    def run(self, request_id: str, output: str) -> ChainRecord:
        """One request end to end. Returns the record, complete or not."""
        kind, p = classify_output(output)
        self.trail.append({"event": "output", "req": request_id,
                           "class": kind})
        rec = ChainRecord(proposal=p)
        if p is None:
            rec.notes.append("answer: nothing to execute")
            return rec
        self.trail.append({"event": "proposal", "req": request_id,
                           "action": p.action, "ref": p.itinerary,
                           "usd": p.amount_usd})
        if self.check_permission:
            rec.permission = self.policy.decide(p)
            if rec.permission is None:
                self.trail.append({"event": "denied", "req": request_id,
                                   "by": POLICY, "to": "person"})
                rec.notes.append("over the limit: sent to a person")
                return rec
            rec.idempotency_key = mint_key(p, rec.permission)
            self.trail.append({"event": "permission", "req": request_id,
                               "id": rec.permission.permission_id,
                               "by": POLICY,
                               "policy": rec.permission.policy_version,
                               "key": rec.idempotency_key})
        return self.execute(request_id, rec)

    def execute(self, request_id: str, rec: ChainRecord) -> ChainRecord:
        p = rec.proposal
        if self.check_permission:
            missing = rec.missing_before_effect(ACTOR)
            if missing:
                self.trail.append({"event": "refused", "req": request_id,
                                   "by": ACTOR, "missing": missing})
                raise Refused(missing)
        attempts = 0
        for attempts in range(1, self.max_attempts + 1):
            try:
                rec.execution = self.world.apply(
                    p.action, p.itinerary, p.amount_usd,
                    rec.idempotency_key)
                break
            except Timeout as exc:
                rec.notes.append(f"attempt {attempts}: {exc}")
        exe = rec.execution or {}
        self.trail.append({"event": "execution", "req": request_id,
                           "by": ACTOR, "attempts": attempts,
                           "effect": exe.get("effect_id"),
                           "status": exe.get("status"),
                           "key": rec.idempotency_key})
        rec.verification = reconcile(self.world, p)
        self.trail.append(dict({"event": "verification",
                                "req": request_id}, **rec.verification))
        missing = rec.missing_after_effect(ACTOR)
        missing = [m for m in missing if m != "trail_entry"]
        state = "verified" if not missing and rec.verification["ok"] \
            else "open"
        rec.trail_entry = self.trail.append(
            {"event": "closed", "req": request_id, "state": state})
        return rec


# ----------------------------------------------------- the demo shape
def demo_shape(world: Network, trail: TrailWriter, request_id: str,
               output: str, max_attempts: int = 3) -> int:
    """October 6: the tool call goes straight to the tool.

    No permission, no key, a retry on every timeout, and one log line
    per call that reports the status the tool sent back. Returns the
    number of calls made.
    """
    kind, p = classify_output(output)
    if p is None:
        return 0
    calls = 0
    for attempt in range(1, max_attempts + 1):
        calls += 1
        try:
            r = world.apply(p.action, p.itinerary, p.amount_usd, key=None)
            trail.append({"event": "tool_call", "req": request_id,
                          "tool": p.action, "status": r["status"]})
            break
        except Timeout:
            trail.append({"event": "tool_call", "req": request_id,
                          "tool": p.action, "status": "timeout"})
    return calls
