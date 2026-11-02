"""The tool gateway: one path for every tool call, read or effect.

Checks, in order, each a named refusal the caller can act on:
  1 auth        the workload token names a known caller
  2 registry    the server and tool are registered and approved
  3 hash        what the server serves matches what was reviewed
  4 scope       this caller may use this tool
  5 mode        code mode may call reads only
  6 arguments   the arguments match the reviewed schema
  7 policy      an effect carries a permission for these arguments
  8 rate        the caller is inside its rate for this tool
Then the call is forwarded and the result capped. Every call, allowed
or refused, writes exactly one trail line, with an argument digest
and never the arguments themselves.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from toolargs import schema
from toolargs.layer import digest

from .registry import APPROVED

FIX = {
    "unauthenticated": "present the workload token for this session",
    "not_registered": "submit the server for registry review",
    "not_approved": "wait for the review decision",
    "description_changed": "resubmit; the served text is not the "
                           "reviewed text",
    "not_in_scope": "this caller's grant does not list the tool",
    "effect_in_code_mode": "propose the effect as a direct call",
    "invalid_arguments": "fix the named field and call again",
    "no_permission": "ask the control plane for a permission",
    "rate_limited": "wait and retry, or hand the case to the desk",
    "output_capped": "ask for a narrower detail level",
}


def tokens_of(obj) -> int:
    """A rough count: four characters to a token."""
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return math.ceil(len(text) / 4)


@dataclass
class Caller:
    sub: str
    tools: frozenset
    rate_per_s: float = 1.0
    burst: int = 10


@dataclass
class Result:
    ok: bool
    reason: str = ""
    field: str = ""
    fix: str = ""
    output: dict | None = None
    call_id: str = ""
    out_tokens: int = 0

    def for_model(self) -> dict:
        if self.ok:
            return self.output or {}
        return {"error": self.reason, "field": self.field,
                "fix": self.fix}


@dataclass
class Bucket:
    level: float
    last: float


class Policy:
    """The control plane's side of contract C3, reduced to a lookup.

    A permission names one tool and one argument digest and is spent
    once. The gateway does not decide effects; it asks.
    """

    def __init__(self):
        self.issued: dict[str, tuple[str, str]] = {}
        self.spent: set[str] = set()

    def issue(self, permission: str, tool: str, args: dict) -> None:
        self.issued[permission] = (tool, digest(tool, args))

    def allows(self, permission: str | None, tool: str, args: dict) -> bool:
        if permission is None or permission in self.spent:
            return False
        if self.issued.get(permission) != (tool, digest(tool, args)):
            return False
        self.spent.add(permission)
        return True


@dataclass
class Gateway:
    registry: object
    servers: dict
    callers: dict
    policy: Policy
    trail: object
    clock: object
    max_out_tokens: int = 2000
    buckets: dict = field(default_factory=dict)
    seq: int = 0

    def call(self, token: str, server: str, tool: str, args: dict,
             via: str = "direct", permission: str | None = None) -> Result:
        self.seq += 1
        cid = f"tc-{self.seq:05d}"
        caller = self.callers.get(token)
        sub = caller.sub if caller else "unknown"
        entry = self.registry.lookup(server, tool)

        def refuse(reason: str, fld: str = "") -> Result:
            self._log(cid, sub, server, tool, via, args, "refused",
                      reason, entry)
            return Result(False, reason, fld, FIX[reason], call_id=cid)

        if caller is None:
            return refuse("unauthenticated")
        if entry is None:
            return refuse("not_registered")
        if entry.status != APPROVED:
            return refuse("not_approved")
        if server not in self.servers:
            return refuse("not_registered")
        srv = self.servers[server]
        if not self.registry.check_served(server, tool,
                                          srv.describe(tool)):
            return refuse("description_changed")
        if tool not in caller.tools:
            return refuse("not_in_scope")
        if via == "code" and entry.kind != "read":
            return refuse("effect_in_code_mode")
        errs = schema.validate(args, entry.schema)
        if errs:
            return refuse("invalid_arguments", errs[0].field)
        if entry.kind == "effect" and not self.policy.allows(
                permission, tool, args):
            return refuse("no_permission")
        if not self._take(sub, tool, caller):
            return refuse("rate_limited")
        out = srv.handle(tool, args)
        n = tokens_of(out)
        if n > self.max_out_tokens:
            self._log(cid, sub, server, tool, via, args, "allowed",
                      "output_capped", entry, n)
            return Result(False, "output_capped", "", FIX["output_capped"],
                          call_id=cid, out_tokens=n)
        self._log(cid, sub, server, tool, via, args, "allowed", "", entry,
                  n)
        return Result(True, output=out, call_id=cid, out_tokens=n)

    def _take(self, sub: str, tool: str, caller: Caller) -> bool:
        now = self.clock.now().timestamp()
        b = self.buckets.setdefault((sub, tool),
                                    Bucket(float(caller.burst), now))
        b.level = min(caller.burst,
                      b.level + (now - b.last) * caller.rate_per_s)
        b.last = now
        if b.level < 1.0:
            return False
        b.level -= 1.0
        return True

    def _log(self, cid, sub, server, tool, via, args, verdict, reason,
             entry, out_tokens=0) -> None:
        self.trail.append({
            "event": "tool_call", "call": cid, "caller": sub,
            "server": server, "tool": tool, "via": via,
            "verdict": verdict, "reason": reason,
            "args_digest": digest(tool, args),
            "desc_hash": entry.desc_hash[:12] if entry else "",
            "out_tokens": out_tokens})


def reconcile(trail_lines: list[str], servers: dict) -> dict:
    """Trail against each server's own count of requests it answered.

    A forwarded call is a trail line with verdict allowed. A server
    that answered more requests than the trail forwarded was reached
    some other way.
    """
    fwd: dict[str, int] = {}
    calls = 0
    for line in trail_lines:
        e = json.loads(line)
        if e.get("event") != "tool_call":
            continue
        calls += 1
        if e["verdict"] == "allowed":
            fwd[e["server"]] = fwd.get(e["server"], 0) + 1
    unmatched = {s: srv.requests - fwd.get(s, 0)
                 for s, srv in servers.items()
                 if srv.requests != fwd.get(s, 0)}
    return {"calls_logged": calls,
            "forwarded": sum(fwd.values()),
            "server_requests": sum(s.requests for s in servers.values()),
            "unmatched": unmatched}
