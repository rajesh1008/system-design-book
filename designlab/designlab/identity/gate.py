"""The gateway, shown a run token instead of a standing account.

`IdentityGateway` is the Chapter 26 gateway with one step in front and
one field more on every trail line. In front: verify the run token
(signature, audience, expiry, revocation), confirm the tool is in the
run's grant, and confirm the itinerary in the arguments is the one the
token names. Then the usual eight checks run, with the run as the
caller. Every line, allowed or refused, carries the customer, the
agent configuration, and the run, the permission if there was one,
and a signature over all of it and the argument digest.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from toolargs.layer import digest

from gateway.core import FIX, Caller, Gateway, Result

from .broker import BrokeredServer, BrokerRefused
from .tokens import Claims, Verifier, sign

TRAIL_KEY = b"designlab identity trail key, lab only"

ID_FIX = {
    "not_a_run_token": "present the run token the control plane "
                       "minted for this case",
    "bad_signature": "the token was altered; ask for a new one",
    "wrong_audience": "this token is for another service",
    "expired": "renew while the case is open, or hand off",
    "revoked": "the run was stopped; do not retry",
    "not_in_run_scope": "this run's grant does not list the tool",
    "wrong_itinerary": "this run may touch only its own itinerary",
    "broker_refused": "the broker would not fill a key for this call",
}


def line_sig(user: str, agent: str, run: str, perm: str,
             args_digest: str) -> str:
    raw = "|".join((user, agent, run, perm, args_digest)).encode()
    return sign(raw, TRAIL_KEY)


@dataclass
class IdentityGateway(Gateway):
    verifier: Verifier = field(default_factory=Verifier)
    _claims: Claims | None = None
    _perm: str = ""

    def call_as(self, token: str, server: str, tool: str, args: dict,
                via: str = "direct",
                permission: str | None = None) -> Result:
        now = self.clock.now().timestamp()
        v = self.verifier.check(token, now)
        self._claims = v.claims
        self._perm = permission or ""
        try:
            if not v.ok:
                return self._refuse_id(v.reason, server, tool, via, args)
            c = v.claims
            if tool not in c.tools:
                return self._refuse_id("not_in_run_scope", server, tool,
                                       via, args)
            trip = args.get("itinerary_id", args.get("booking_ref"))
            if trip is not None and trip != c.itinerary:
                return self._refuse_id("wrong_itinerary", server, tool,
                                       via, args, "itinerary_id")
            self.callers[c.jti] = Caller(c.run, frozenset(c.tools))
            srv = self.servers.get(server)
            if isinstance(srv, BrokeredServer):
                srv.claims = c
            try:
                return self.call(c.jti, server, tool, args, via,
                                 permission)
            except BrokerRefused as e:
                return self._refuse_id("broker_refused", server, tool,
                                       via, args, e.reason)
            finally:
                self.callers.pop(c.jti, None)
                if isinstance(srv, BrokeredServer):
                    srv.claims = None
        finally:
            self._claims = None
            self._perm = ""

    def _refuse_id(self, reason, server, tool, via, args,
                   fld: str = "") -> Result:
        self.seq += 1
        cid = f"tc-{self.seq:05d}"
        entry = self.registry.lookup(server, tool)
        self._log(cid, "unknown", server, tool, via, args, "refused",
                  reason, entry)
        return Result(False, reason, fld, ID_FIX[reason], call_id=cid)

    def _log(self, cid, sub, server, tool, via, args, verdict, reason,
             entry, out_tokens=0) -> None:
        c = self._claims
        user, agent, run = (c.sub, c.act, c.run) if c else ("", "", "")
        d = digest(tool, args)
        self.trail.append({
            "event": "tool_call", "call": cid, "caller": sub,
            "server": server, "tool": tool, "via": via,
            "verdict": verdict, "reason": reason,
            "args_digest": d, "user": user, "agent": agent,
            "run": run, "perm": self._perm,
            "sig": line_sig(user, agent, run, self._perm, d) if c else "",
            "desc_hash": entry.desc_hash[:12] if entry else "",
            "out_tokens": out_tokens})


assert set(ID_FIX).isdisjoint(FIX)


@dataclass
class SessionGateway(Gateway):
    """The gateway as Chapter 26 left it, for the trail check.

    The line names the customer, the agent configuration, and the case
    from the session, but nothing on it is signed, no permission is
    bound to those names, and the call reaches the system of record on
    the one standing account.
    """
    session: tuple = ("", "", "")

    def _log(self, cid, sub, server, tool, via, args, verdict, reason,
             entry, out_tokens=0) -> None:
        user, agent, case = self.session
        self.trail.append({
            "event": "tool_call", "call": cid, "caller": sub,
            "server": server, "tool": tool, "via": via,
            "verdict": verdict, "reason": reason,
            "args_digest": digest(tool, args), "user": user,
            "agent": agent, "run": case, "perm": "", "sig": "",
            "desc_hash": entry.desc_hash[:12] if entry else "",
            "out_tokens": out_tokens})
