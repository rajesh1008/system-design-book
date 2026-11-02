"""Build the June 2026 world: registry, servers, callers, gateway.

The fourteen tools of harness 1.0.0 were reviewed and approved by Owen
Fletcher on Thursday, June 4, 2026, before the release of June 8. The
clock starts there, in Chicago time. Lakeshore figures are
illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.clock import FixedClock
from common.trail import TrailWriter

from .core import Caller, Gateway, Policy
from .registry import Registry
from .search import synthetic
from .servers import (EFFECT_SCOPE, READ_SCOPE, ToolServer,
                      lakeshore_servers)

REVIEWER = "Owen Fletcher"
SERVICING = "wl-servicing-agent"
DESK = "wl-desk-assistant"


@dataclass
class World:
    registry: Registry
    servers: dict
    callers: dict
    policy: Policy
    gateway: Gateway
    trail: TrailWriter
    clock: FixedClock


def scope_for(kind: str) -> tuple[str, ...]:
    return (EFFECT_SCOPE,) if kind == "effect" else (READ_SCOPE,)


def build(extra_tools: int = 0,
          start: str = "2026-06-04T10:00:00-05:00") -> World:
    clock = FixedClock(start=start, step_seconds=0.05)
    trail = TrailWriter(clock=clock)
    reg = Registry(trail, clock)
    servers = lakeshore_servers()
    for name, srv in servers.items():
        for t in srv.tools():
            spec = srv.describe(t)
            reg.submit(name, spec, scope_for(spec["kind"]), srv.owner)
            reg.review(name, t, REVIEWER, approve=True,
                       note="harness 1.0.0")
    fourteen = frozenset(t for s in servers.values() for t in s.tools())
    if extra_tools:
        by_server: dict[str, dict] = {}
        for server, spec in synthetic(extra_tools):
            by_server.setdefault(server, {})[spec["name"]] = spec
        for server, tools in by_server.items():
            srv = ToolServer(server, tools, owner=f"{server} owners")
            servers[server] = srv
            for t in srv.tools():
                spec = srv.describe(t)
                reg.submit(server, spec, scope_for(spec["kind"]),
                           srv.owner)
                reg.review(server, t, REVIEWER, approve=True,
                           note="catalog")
    every = frozenset(e.tool for e in reg.approved())
    callers = {SERVICING: Caller("agent:servicing", fourteen),
               DESK: Caller("desk:assistant-pilot", every)}
    policy = Policy()
    gw = Gateway(reg, servers, callers, policy, trail, clock)
    return World(reg, servers, callers, policy, gw, trail, clock)
