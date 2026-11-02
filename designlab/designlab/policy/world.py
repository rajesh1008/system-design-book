"""Build June 2026 with the engine and the switch in the gateway.

Reuses gateway.world.build for the registry, the fourteen tools, the
callers, the trail and the clock, and puts a PolicyGateway in place of
the plain one. The bundles are proposed, signed and activated in the
order Lakeshore ran them. Lakeshore figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass

from gateway.core import Caller
from gateway.world import DESK, SERVICING, build as build_gateway

from .approval import ApprovalGate, Approver
from .bundle import BundleStore
from .engine import PolicyEngine
from .gate import PolicyGateway
from .kill import KillSwitch
from .rules import AUTHOR, BUNDLES, SIGNER

FARE_WATCH = "wl-fare-watch"
TERESA = Approver("Teresa Alvarez", "team lead", "person:t.alvarez")
JOANNA = Approver("Joanna Reyes", "desk agent", "person:j.reyes")


@dataclass
class PWorld:
    gateway: PolicyGateway
    engine: PolicyEngine
    bundles: BundleStore
    approvals: ApprovalGate
    switch: KillSwitch
    servers: dict
    trail: object
    clock: object


def build(active: str = "pb-2026.06.22", shadow: str | None = None,
          start: str = "2026-06-22T09:00:00-05:00",
          switch: KillSwitch | None = None) -> PWorld:
    w = build_gateway(start=start)
    store = BundleStore(w.clock)
    for rev in BUNDLES:
        store.propose(rev, BUNDLES[rev], AUTHOR)
        store.sign(rev, SIGNER)
        store.move(rev, "shadow", AUTHOR)
        if rev == shadow:
            break
        store.move(rev, "active", AUTHOR)
        if rev == active:
            break
    gate = ApprovalGate(w.clock)
    engine = PolicyEngine(store, gate, w.trail, w.clock)
    callers = dict(w.callers)
    reads = frozenset(t for t in w.callers[SERVICING].tools
                      if t in ("booking_read", "offers_search",
                               "fare_calc"))
    callers[FARE_WATCH] = Caller("loop:fare-watch",
                                 reads | {"voucher_issue"})
    gw = PolicyGateway(w.registry, w.servers, callers, engine.policy,
                       w.trail, w.clock, engine=engine,
                       switch=switch or KillSwitch())
    return PWorld(gw, engine, store, gate, gw.switch, w.servers,
                  w.trail, w.clock)


__all__ = ["build", "PWorld", "SERVICING", "DESK", "FARE_WATCH",
           "TERESA", "JOANNA"]
