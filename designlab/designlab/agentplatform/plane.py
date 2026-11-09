"""The shared control plane: the Chapter 32 identity, the Chapter 25
gateway and registry, the Chapter 31 policy engine, the trace, and
the trail, built once and driven by manifests.

What changed in the extraction is small and is all here. Callers come
from manifests instead of code. A run token binds the resource the
manifest names (an itinerary for servicing and the desk, a member for
loyalty) instead of always an itinerary. Bundles carry rules from
more than one team. The verifier reads through the source a manifest
declares, and says so in its record.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from gateway.core import Caller, Result, reconcile
from gateway.servers import EFFECT_SCOPE, READ_SCOPE, ToolServer
from identity.tokens import Claims, Verifier, encode
from policy.rules import AUTHOR, SIGNER
from policy.world import DESK, SERVICING, build as build_policy

from .template import RESOURCES

from tracing import conventions as conv
from tracing.spans import Tracer

START = "2026-08-14T09:00:00-05:00"
REVIEWER = "Owen Fletcher"
EVAL_OWNER = "Ben Carter"
PLATFORM_VERIFIER = "verify:platform"


@dataclass
class RunResult:
    use_case: str
    run: str
    calls: list = field(default_factory=list)   # (tool, Result)

    @property
    def ok(self) -> bool:
        return all(r.ok for _, r in self.calls)


@dataclass
class ControlPlane:
    world: object
    manifests: dict = field(default_factory=dict)
    verifier: Verifier = field(default_factory=Verifier)
    spans: list = field(default_factory=list)
    runs: int = 0

    # -- the parts, by their owners' names -------------------------------
    @property
    def gateway(self):
        return self.world.gateway

    @property
    def registry(self):
        return self.world.gateway.registry

    @property
    def trail(self):
        return self.world.trail

    @property
    def clock(self):
        return self.world.clock

    def lines(self) -> list[dict]:
        return [json.loads(x) for x in self.trail.lines]

    # -- callers from manifests -------------------------------------------
    def admit(self, m: dict) -> Caller:
        """The identity step: one caller per use case, with exactly the
        tools its manifest declares."""
        u = m["use_case"]
        tools = frozenset(t["name"] for t in m["tools"])
        caller = Caller(u["identity"], tools)
        self.gateway.callers[u["caller_key"]] = caller
        self.manifests[u["name"]] = m
        return caller

    def retire(self, key: str) -> None:
        self.gateway.callers.pop(key, None)

    def kind_of(self, server: str, tool: str) -> str:
        e = self.registry.lookup(server, tool)
        return e.kind if e else "unknown"

    # -- registry -----------------------------------------------------------
    def submit_tools(self, m: dict) -> list[tuple[str, list[str]]]:
        """New tools a use case brings: served by its team, submitted to
        the shared registry, screened. Returns (tool, findings)."""
        u = m["use_case"]
        new = [t for t in m["tools"] if "input_schema" in t]
        by_server: dict[str, dict] = {}
        for t in new:
            spec = {k: t[k] for k in ("name", "version", "kind",
                                       "description", "input_schema")}
            by_server.setdefault(t["server"], {})[t["name"]] = spec
        out = []
        for server, tools in by_server.items():
            srv = ToolServer(server, tools, owner=u["team"])
            self.world.servers[server] = srv
            self.gateway.servers[server] = srv
            for name in srv.tools():
                spec = srv.describe(name)
                scope = READ_SCOPE if spec["kind"] == "read" \
                    else EFFECT_SCOPE
                e = self.registry.submit(server, spec, (scope,),
                                         srv.owner)
                out.append((name, list(e.findings)))
        return out

    def approve_tools(self, m: dict, note: str) -> None:
        for t in m["tools"]:
            if "input_schema" in t:
                self.registry.review(t["server"], t["name"], REVIEWER,
                                     approve=True, note=note)

    # -- policy -------------------------------------------------------------
    def add_rules(self, rev: str, m: dict, author: str) -> None:
        """A use case's rules join the shared bundle: proposed by its
        team, signed by someone else, shadowed, then made active."""
        base = list(self.world.bundles.active().rules)
        rules = base + list(m.get("policy", {}).get("rules", []))
        b = self.world.bundles
        b.propose(rev, rules, author)
        b.sign(rev, SIGNER)
        b.move(rev, "shadow", author)
        b.move(rev, "active", author)

    # -- runs ---------------------------------------------------------------
    def mint(self, m: dict, resource: str, tools=None) -> str:
        u = m["use_case"]
        self.runs += 1
        now = self.clock.now().timestamp()
        c = Claims(sub=f"customer:{resource}", act=u["identity"],
                   run=f"run-{u['name']}-{self.runs:04d}",
                   itinerary=resource,
                   tools=tuple(tools or (t["name"] for t in m["tools"])),
                   iat=now, exp=now + 900, jti=f"j-{self.runs:05d}")
        return encode(c)

    def call(self, m: dict, token: str, server: str, tool: str,
             args: dict, tracer: Tracer):
        """Identity first, then the policy gateway, then the platform's
        verifier for an effect that went through."""
        u = m["use_case"]
        v = self.verifier.check(token, self.clock.now().timestamp())
        refused = ""
        if not v.ok:
            refused = v.reason
        elif v.claims.act != u["identity"]:
            refused = "wrong_agent"
        elif tool not in v.claims.tools:
            refused = "not_in_token"
        else:
            fields = RESOURCES[u["resource"]]
            got = next((args[f] for f in fields if f in args), None)
            if got is not None and got != v.claims.itinerary:
                refused = "other_resource"
        with tracer.span(conv.tool_name(tool), "CLIENT", **{
                conv.OP: "execute_tool", conv.TOOL_NAME: tool,
                conv.AGENT_NAME: u["name"]}) as s:
            if refused:
                self.trail.append({"event": "identity_refused",
                                   "use_case": u["name"], "tool": tool,
                                   "reason": refused})
                r = Result(False, refused)
            else:
                r = self.gateway.call(u["caller_key"], server, tool,
                                      args, session=v.claims.run)
            if s is not None:
                s.attrs[conv.TOOL_CALL] = r.call_id
                s.attrs[conv.VERDICT] = "allowed" if r.ok else r.reason
                self.spans.append(s)
            tracer.advance(40)
        if r.ok and self.kind_of(server, tool) == "effect":
            self.verify(m, r.call_id, tool, args)
        return r

    def verify(self, m: dict, call_id: str, tool: str, args: dict):
        v = m["verify"]
        self.trail.append({"event": "verification", "call": call_id,
                           "use_case": m["use_case"]["name"],
                           "tool": tool, "verifier": PLATFORM_VERIFIER,
                           "source": v["source"],
                           "reads_through": v["reads_through"],
                           "confirmed": True})

    def run(self, name: str, n: int | None = None,
            skip_spans: bool = False) -> RunResult:
        m = self.manifests[name]
        n = self.runs + 1 if n is None else n
        script = [(s["server"], s["tool"], {
            k: (val.format(n=n) if isinstance(val, str) else val)
            for k, val in s["args"].items()}) for s in m["script"]]
        fields = RESOURCES[m["use_case"]["resource"]]
        resource = next(a[f] for _, _, a in script for f in fields
                        if f in a)
        token = self.mint(m, resource)
        tr = Tracer(f"{name}-{n}", skip=("execute_tool",)
                    if skip_spans else ())
        out = RunResult(name, f"{name}-{n}")
        for server, tool, args in script:
            out.calls.append((tool, self.call(m, token, server, tool,
                                              args, tr)))
        self.clock.advance(30)
        return out

    def reconcile(self) -> dict:
        return reconcile(self.trail.lines, self.world.servers)


def build(start: str = START) -> ControlPlane:
    """The plane as it stood on Friday, August 14, 2026: the June
    world, with the hard-wired callers removed."""
    w = build_policy(start=start)
    p = ControlPlane(w)
    for key in (SERVICING, DESK):
        p.retire(key)
    return p


__all__ = ["ControlPlane", "build", "REVIEWER", "AUTHOR", "SIGNER",
           "EVAL_OWNER", "PLATFORM_VERIFIER", "RunResult"]
