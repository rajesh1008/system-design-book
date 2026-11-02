"""The gateway with the engine and the switch in its path.

A subclass of Chapter 25's gateway, not a fork: its eight checks still
run, in order, on every call that gets that far. Two things come
first. The kill switch is read before anything else, because a stop
must not depend on the engine being up. Then the engine decides the
call: every read is evaluated against the active bundle, and an effect
that arrives without a permission is a proposal, decided here, so no
path exists where an effect skips the engine.

When the engine is down, effects fail closed. Reads continue against
the gateway's cached copy of the last read rules, for at most 60
seconds, and each is logged as cached.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from gateway.core import Gateway, Result
from gateway.registry import APPROVED
from toolargs import schema

from .engine import EngineDown, PolicyEngine, Request
from .kill import FIX as KILL_FIX
from .kill import Held, KillSwitch, new_hold_queue

FIX = dict(KILL_FIX, **{
    "approval_needed": "wait for the approver; the case shows the card",
    "routed_to_person": "the case is with the named desk",
    "policy_denied": "the engine refused; the reason names the rule",
    "policy_unavailable": "effects fail closed; propose again later",
})
READ_CACHE_S = 60.0


@dataclass
class PolicyGateway(Gateway):
    engine: PolicyEngine | None = None
    switch: KillSwitch = field(default_factory=KillSwitch)
    replica_lag_s: float = 0.0
    held: object = field(default_factory=new_hold_queue)
    last_decision: object = None
    cache_until: float = 0.0
    counts: dict = field(default_factory=dict)

    def call(self, token, server, tool, args, via="direct",
             permission=None, session="s-0", traveler="") -> Result:
        caller = self.callers.get(token)
        sub = caller.sub if caller else "unknown"
        entry = self.registry.lookup(server, tool)
        kind = entry.kind if entry else "unknown"
        now = self.clock.now()
        self.last_decision = None

        stop = self.switch.blocks(sub, tool, kind, now,
                                  self.replica_lag_s)
        if stop:
            if kind == "effect" and stop != "agent_off":
                self.held.hold(now.timestamp(),
                               Held(tool, args, permission or "",
                                    session))
            return self._refuse(sub, server, tool, via, args, entry,
                                stop)
        if (caller is None or entry is None or entry.status != APPROVED
                or tool not in caller.tools
                or schema.validate(args, entry.schema)):
            self._count("gateway_refused")
            return super().call(token, server, tool, args, via,
                                permission)
        try:
            if kind != "effect" or permission is None:
                d = self.engine.decide(Request(sub, tool, kind, args,
                                               session, traveler))
                self.last_decision = d
                self.cache_until = now.timestamp() + READ_CACHE_S
                self._count("engine_decided")
                if d.verdict == "approve":
                    return self._refuse(sub, server, tool, via, args,
                                        entry, "approval_needed",
                                        d.card)
                if d.verdict == "route":
                    return self._refuse(sub, server, tool, via, args,
                                        entry, "routed_to_person",
                                        d.route)
                if d.verdict == "deny":
                    return self._refuse(sub, server, tool, via, args,
                                        entry, "policy_denied", d.reason)
                if kind == "effect":
                    permission = d.permission
            else:
                self._count("permission_presented")
        except EngineDown:
            if kind == "effect" or now.timestamp() > self.cache_until:
                return self._refuse(sub, server, tool, via, args, entry,
                                    "policy_unavailable")
            self._count("read_cached")
        r = super().call(token, server, tool, args, via, permission)
        if not r.ok and r.reason == "no_permission":
            r.field = self.engine.policy.last
        return r

    def _refuse(self, sub, server, tool, via, args, entry, reason,
                detail="") -> Result:
        self.seq += 1
        cid = f"tc-{self.seq:05d}"
        self._count(reason)
        self._log(cid, sub, server, tool, via, args, "refused", reason,
                  entry)
        return Result(False, reason, detail, FIX[reason], call_id=cid)

    def _count(self, k: str) -> None:
        self.counts[k] = self.counts.get(k, 0) + 1
