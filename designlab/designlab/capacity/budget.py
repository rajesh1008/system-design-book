"""Latency budgets per plane, trace replay, and the p95 prediction.

Task latency is the agent's working time from the customer's request
to the answer or the hand-off. Time spent waiting on the customer or
on an approver is not in it; those are the session's, not the task's.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from common.rand import seeded

from .stats import pct

# Seconds at p95 per plane, adopted March 3, 2026. The lines do not
# add to the task's p95: tails of parts rarely land on the same task.
PLANE_BUDGET = {
    "knowledge": 1.0,
    "model": 20.0,
    "queue": 2.0,           # rate-limit waits at the provider
    "retries": 3.0,         # timed-out model and tool attempts
    "tools": 20.0,
    "control": 0.3,         # gateway plus policy, every tool call
    "trail": 0.4,
    "loop": 0.6,
}
TASK_BUDGET_S = 40.0
PLANES = tuple(PLANE_BUDGET)


@dataclass(frozen=True)
class Design:
    own_limit: bool = False         # pilot's own provider limit
    repeat_cap: int | None = None   # re-searches allowed per task
    step_cap: int | None = None     # hard stop, hand off to a person
    prefetch: bool = False          # fare rules off the critical path
    retry_scale: float = 1.0        # multiply retries seen


AS_RUN = Design()
OWN = Design(own_limit=True)
MARCH = Design(own_limit=True, repeat_cap=1, step_cap=24)


def _kept(steps, d: Design):
    out, rep = [], 0
    for x in steps:
        if x.repeat and d.repeat_cap is not None:
            rep += 1
            if rep > d.repeat_cap:
                continue
        out.append(x)
    handoff = d.step_cap is not None and len(out) > d.step_cap
    return (out[:d.step_cap] if handoff else out), handoff


def step_planes(x, d: Design) -> dict[str, float]:
    """Seconds one step spends in each plane, under a design."""
    k = d.retry_scale
    wait = x.wait_own if d.own_limit else x.wait_shared
    first = x.tool_s[0] if x.tool_s else 0.0
    if d.prefetch and x.tool == "fare_rules":
        first = 0.0                  # fetched while the model ran
    extra = sum(x.tool_s[1:]) + x.error_s
    return {"knowledge": 0.0, "model": sum(x.model_s),
            "queue": wait * k, "retries": extra * k, "tools": first,
            "control": sum(x.gate_s), "trail": x.trail_s,
            "loop": x.loop_s}


def task_planes(s, d: Design) -> tuple[dict[str, float], bool]:
    steps, handoff = _kept(s.steps, d)
    tot = dict.fromkeys(PLANES, 0.0)
    tot["knowledge"] = s.knowledge_s
    for x in steps:
        for p, v in step_planes(x, d).items():
            tot[p] += v
    return tot, handoff


@dataclass
class Replay:
    design: Design
    latencies: list[float]
    handoffs: int
    plane_p95: dict[str, float] = field(default_factory=dict)

    @property
    def p95(self) -> float:
        return pct(self.latencies, 0.95)

    @property
    def median(self) -> float:
        return pct(self.latencies, 0.5)

    @property
    def handoff_share(self) -> float:
        return self.handoffs / len(self.latencies)


def replay(sessions, d: Design = AS_RUN) -> Replay:
    """Replay every task in the traces under a design."""
    lat, per, hand = [], {p: [] for p in PLANES}, 0
    for s in sessions:
        if not s.is_task:
            continue
        planes, h = task_planes(s, d)
        hand += h
        lat.append(sum(planes.values()))
        for p, v in planes.items():
            per[p].append(v)
    return Replay(d, lat, hand, {p: pct(v, 0.95) for p, v in per.items()})


def check_budget(r: Replay, budget: float = TASK_BUDGET_S):
    """Rows of (plane, p95, budget, ok) and the task line."""
    rows = [(p, r.plane_p95[p], PLANE_BUDGET[p],
             r.plane_p95[p] <= PLANE_BUDGET[p]) for p in PLANES]
    rows.append(("task", r.p95, budget, r.p95 <= budget))
    return rows


def predict(sessions, fit, mode: str = "task", n: int = 20000,
            seed: int = 0, d: Design = AS_RUN) -> float:
    """Predict task p95 before replaying it.

    mode "task": draw a step count from the fitted lognormal, then
    that many step times from the traces, and sum; take the p95.
    mode "call": the provider's per-call p95 times the median step
    count. It is the shortcut the pilot's first sheet used."""
    if mode == "call":
        return fit.call_p95_s * fit.steps_median
    if mode != "task":
        raise ValueError(f"unknown mode {mode!r}")
    pool = [sum(step_planes(x, d).values())
            for s in sessions if s.is_task for x in s.steps]
    know = [s.knowledge_s for s in sessions if s.is_task]
    rng: random.Random = seeded(seed, "capacity-predict")
    mu, sigma = math.log(fit.steps_median), fit.steps_sigma
    out = []
    for _ in range(n):
        k = max(2, round(math.exp(rng.gauss(mu, sigma))))
        out.append(rng.choice(know)
                   + sum(rng.choice(pool) for _ in range(k)))
    return pct(out, 0.95)
