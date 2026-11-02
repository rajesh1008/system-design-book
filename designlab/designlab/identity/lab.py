"""Build the June 22, 2026 world: the Chapter 26 gateway behind run
tokens, the broker in front of the systems of record. Lakeshore
figures are illustrative.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.ids import run_id
from common.rand import seeded

from gateway.world import build

from .broker import BrokeredServer, SecretBroker
from .delegate import AgentConfig, ControlPlane, Session
from .gate import IdentityGateway
from .tokens import Verifier

START = "2026-06-22T10:00:00-05:00"
CUSTOMER = "C-118204"
TRIP = "LTG-5208877"
OTHER_TRIP = "LTG-5310442"
TICKET = "TKT-40210"
# server -> the system of record behind it
SYSTEMS = {"booking": "bookings", "payments": "payments",
           "messaging": "profiles", "documents": "documents"}
REFUND = {"itinerary_id": TRIP, "ticket_number": TICKET,
          "amount_usd": "250.00", "reason": "canceled_by_carrier"}


@dataclass
class IdWorld:
    gw: IdentityGateway
    cp: ControlPlane
    broker: SecretBroker
    verifier: Verifier
    agent: AgentConfig
    session: Session
    base: object

    def new_run(self) -> str:
        return run_id("run", self.base.clock,
                      seeded(32, "run", str(len(self.cp.minted))))


def servicing_agent(tools) -> AgentConfig:
    return AgentConfig("servicing", "servicing-1.0.0", frozenset(tools))


def build_id(start: str = START) -> IdWorld:
    w = build(start=start)
    broker = SecretBroker(sorted(set(SYSTEMS.values())))
    servers = dict(w.servers)
    for name, system in SYSTEMS.items():
        servers[name] = BrokeredServer(w.servers[name], broker, system)
    verifier = Verifier()
    gw = IdentityGateway(w.registry, servers, {}, w.policy, w.trail,
                         w.clock, verifier=verifier)
    agent = servicing_agent(w.callers["wl-servicing-agent"].tools)
    session = Session(CUSTOMER, frozenset({TRIP}))
    return IdWorld(gw, ControlPlane(w.clock), broker, verifier, agent,
                   session, w)
