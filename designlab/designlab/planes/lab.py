"""Build the four planes and replay a seeded week of pilot traffic.

`build()` wires the planes the way the reference architecture draws them.
`build(bypass=True)` adds the injected failure: a fast-path refund tool
that holds its own processor client. `cases()` is a seeded week of
January pilot work across the four task types in autonomy.toml.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from common.clock import FixedClock
from common.rand import seeded

from .action import AgentLoop, FastPathRefund, Gateway, GatewayTool
from .autonomy import load_autonomy
from .control import ControlPlane
from .knowledge import Fact, KnowledgePlane
from .trailplane import TrailPlane
from .world import World

START = "2026-01-12T14:00:00+00:00"
MIX = (("refund", 0.30), ("rebook", 0.50), ("voucher", 0.15),
       ("hotel_cancel", 0.05))


@dataclass
class System:
    world: World
    knowledge: KnowledgePlane
    control: ControlPlane
    trail: TrailPlane
    gateway: Gateway
    loop: AgentLoop


class Approvers:
    """The refund approver desk. Names are roles, not people."""

    def pick(self, case) -> str:
        return f"approver:desk-{case['n'] % 4 + 1}"


def cases(seed: int = 6, n: int = 800) -> list[dict]:
    r = seeded(seed, "planes", "cases")
    out = []
    for i in range(n):
        x, task = r.random(), "hotel_cancel"
        acc = 0.0
        for name, share in MIX:
            acc += share
            if x < acc:
                task = name
                break
        usd = {"refund": lambda: round(r.uniform(60, 1600), 2),
               "rebook": lambda: round(r.uniform(0, 290), 2),
               "voucher": lambda: r.choice([25, 50, 75, 100, 100, 150]),
               "hotel_cancel": lambda: 0.0}[task]()
        out.append({
            "n": i, "day": i * 7 // n, "task": task, "itinerary": f"LTG-{5200000 + i}",
            "usd": float(usd),
            "fact_age_s": r.choice([30] * 60 + [300] * 38 + [4000] * 2),
            "approver_s": round(r.lognormvariate(4.2, 0.6), 1),
            "lost": r.random() < 0.005,
        })
    return out


def knowledge_for(batch: list[dict]) -> KnowledgePlane:
    now = datetime.fromisoformat(START)
    records = {}
    for c in batch:
        as_of = (now - timedelta(seconds=c["fact_age_s"])).isoformat()
        records[c["itinerary"]] = [
            Fact("fare_rules", "same-carrier", "airline-fares", as_of),
            Fact("payment_card", "on-file", "payment-profile", as_of)]
    return KnowledgePlane(records, FixedClock(START, step_seconds=0))


def build(batch: list[dict], bypass: bool = False,
          policy_in_loop: bool = False, table=None) -> System:
    world = World()
    trail = TrailPlane(world, FixedClock(START, step_seconds=1))
    control = ControlPlane(table or load_autonomy(), trail)
    gateway = Gateway(world, control, trail)
    tools = {t: GatewayTool(gateway, t)
             for t in ("refund", "rebook", "voucher")}
    if bypass:
        tools["refund_fast"] = FastPathRefund(world)
    knowledge = knowledge_for(batch)
    loop = AgentLoop(knowledge, control, trail, tools, policy_in_loop)
    return System(world, knowledge, control, trail, gateway, loop)


def replay(system: System, batch: list[dict]) -> dict:
    outcomes, day = [], None
    for c in batch:
        if c.get("day") != day:
            system.control.new_day()
            day = c.get("day")
        outcomes.append(system.loop.run(c, Approvers()))
    s = {"cases": len(outcomes), "outcomes": outcomes,
         "by_level": Counter(o.level for o in outcomes),
         "path": Counter(o.path for o in outcomes),
         "customer": Counter(o.customer for o in outcomes),
         "handoff": Counter(o.handoff for o in outcomes if o.handoff)}
    s["model_done_unverified"] = sum(
        1 for o in outcomes if o.model_said == "done"
        and o.customer != "done")
    s["told_done_unverified"] = sum(
        1 for o in outcomes if o.customer == "done"
        and not _verified(system, o))
    s["effects"] = len(system.world.effects)
    s["gateway_effects"] = system.gateway.calls
    s["unmediated"] = len(system.world.unmediated())
    s["trail_ok"] = system.trail.intact()
    s["decisions"] = system.trail.count("decision")
    sync = [o.waited_s for o in outcomes if o.handoff == "sync"]
    s["sync_p50_s"] = sorted(sync)[len(sync) // 2] if sync else 0.0
    return s


def _verified(system: System, o) -> bool:
    for line in system.trail.writer.lines:
        if (o.itinerary in line and '"kind": "verification"' in line
                and '"ok": true' in line):
            return True
    return False
