"""The control plane mints a run's identity at grant: delegation.

RFC 8693 separates delegation (the actor keeps its own identity and
acts for the subject; the token says both) from impersonation (the
actor becomes the subject; the token says only the subject). Here the
customer's session is the subject token and the agent configuration
is the actor. The exchange narrows: one itinerary the customer owns,
the tools the configuration was reviewed for, and no longer than the
case's permission window. A child token may narrow a parent and may
never widen it.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass

from .tokens import RUN_TTL_S, Claims, _b64, encode, sign


@dataclass(frozen=True)
class Session:
    """The subject: a signed-in customer and the trips they own."""
    customer: str
    itineraries: frozenset


@dataclass(frozen=True)
class AgentConfig:
    """The actor: a reviewed agent configuration, not a person."""
    name: str
    release: str
    tools: frozenset

    @property
    def id(self) -> str:
        return f"agent:{self.name}@{self.release}"


class Refused(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class ControlPlane:
    """Mints run tokens. Holds no system-of-record credential."""

    def __init__(self, clock, seed: int = 32):
        self.clock = clock
        self.rng = random.Random(seed)
        self.minted: list[Claims] = []

    def _jti(self) -> str:
        return f"rt-{self.rng.getrandbits(32):08x}"

    def delegate(self, session: Session, agent: AgentConfig, run: str,
                 itinerary: str, tools: set,
                 ttl_s: int = RUN_TTL_S) -> str:
        if itinerary not in session.itineraries:
            raise Refused("not_customers_itinerary")
        if not set(tools) <= agent.tools:
            raise Refused("tool_not_reviewed")
        if ttl_s > RUN_TTL_S:
            raise Refused("lifetime_over_window")
        now = self.clock.now().timestamp()
        c = Claims(sub=session.customer, act=agent.id, run=run,
                   itinerary=itinerary, tools=tuple(sorted(tools)),
                   iat=now, exp=now + ttl_s, jti=self._jti())
        self.minted.append(c)
        return encode(c)

    def impersonate(self, session: Session, itinerary: str,
                    tools: set) -> str:
        """For comparison only: the borrowed identity card. The token
        names the customer and nobody else; the actor has vanished."""
        now = self.clock.now().timestamp()
        body = Claims(sub=session.customer, act="", run="",
                      itinerary=itinerary, tools=tuple(sorted(tools)),
                      iat=now, exp=now + RUN_TTL_S, jti=self._jti())
        d = body.as_dict()
        d.pop("act")
        d.pop("run")
        raw = json.dumps(d, sort_keys=True).encode()
        return f"{_b64(raw)}.{sign(raw)}"


def attenuate(parent: Claims, tools: set, ttl_s: float,
              now: float) -> Claims:
    """A child for a sub-step: subset of tools, same trip, sooner end,
    the same actor lineage. Anything else is refused."""
    if not set(tools) <= set(parent.tools):
        raise Refused("scope_widened")
    exp = now + ttl_s
    if exp > parent.exp:
        raise Refused("lifetime_widened")
    return Claims(sub=parent.sub, act=parent.act, run=parent.run,
                  itinerary=parent.itinerary, tools=tuple(sorted(tools)),
                  iat=now, exp=exp, jti=parent.jti + ".1")
