"""The three-tier kill switch, enforced at the gateway (Chapter 12).

Tier one holds one tool's effects, which is the manual form of a
breaker. Tier two holds every effect at the gateway while proposals
and permissions continue, the propose-only rung for everything. Tier
three turns the agent off, the people-only rung: every call from the
agent's identity is refused, its token is revoked, and the harness
admits no new run.

The switch is a flag every gateway replica reads on its own poll, so
a pull reaches each replica within one poll interval. Pulling it
returns an acknowledgment, and an acknowledgment is the first of four
facts a stop needs, not the stop:

  received            the switch recorded the pull
  no new commands     the far end saw no new effect after propagation
  in-flight settled   every effect already sent finished or timed out
  safe state observed a quiet window at the far end, by its own count
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from failure.degrade import HoldQueue, rung

TIERS = {1: "one tool's effects held", 2: "every effect held",
         3: "agent off"}
FIX = {"tool_held": "the tool is held; the case goes to a person",
       "effects_held": "effects are held; propose, and a person "
                       "or the release will act",
       "agent_off": "the agent is off; the contact goes to a person"}


@dataclass
class Pull:
    at: datetime
    tier: int
    by: str
    reason: str
    tool: str = ""
    key: str = "kill/servicing"


@dataclass
class KillSwitch:
    """One flag store. `read_key` is what the gateways read; a pull
    writes `write_key`. They differ only in the broken drill."""
    pulls: list[Pull] = field(default_factory=list)
    write_key: str = "kill/servicing"
    read_key: str = "kill/servicing"
    poll_s: float = 5.0

    def pull(self, at: datetime, tier: int, by: str, reason: str,
             tool: str = "") -> dict:
        if tier not in TIERS or (tier == 1 and not tool):
            raise ValueError("tier one names a tool; tiers are 1 to 3")
        self.pulls.append(Pull(at, tier, by, reason, tool,
                               self.write_key))
        return {"status": 200, "received": True, "tier": tier,
                "at": at.isoformat(timespec="seconds")}

    def clear(self, at: datetime, by: str) -> dict:
        self.pulls.append(Pull(at, 0, by, "clear", "", self.write_key))
        return {"status": 200, "received": True, "tier": 0}

    def state(self, now: datetime, lag_s: float = 0.0) -> Pull | None:
        """What a replica that last polled `lag_s` ago sees."""
        seen = now - timedelta(seconds=lag_s)
        live = [p for p in self.pulls
                if p.key == self.read_key and p.at <= seen]
        if not live or live[-1].tier == 0:
            return None
        return live[-1]

    def blocks(self, sub: str, tool: str, kind: str, now: datetime,
               lag_s: float = 0.0) -> str:
        p = self.state(now, lag_s)
        if p is None:
            return ""
        if p.tier == 3 and sub.startswith("agent:"):
            return "agent_off"
        if p.tier >= 2 and kind == "effect":
            return "effects_held"
        if p.tier == 1 and kind == "effect" and tool == p.tool:
            return "tool_held"
        return ""

    def ladder_rung(self, now: datetime) -> str:
        p = self.state(now)
        return rung(kill_tier=p.tier if p else 0)


@dataclass
class Held:
    tool: str
    args: dict
    permission: str
    session: str


def new_hold_queue() -> HoldQueue:
    return HoldQueue()
