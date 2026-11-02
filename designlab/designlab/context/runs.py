"""Seeded long runs: the April traces the chapter replays.

A run is a list of steps. Each step adds a model turn and a tool
result to the history, may add a customer message, may retrieve fare-
rule passages for that step only, and may introduce a fact the rest of
the run depends on: a customer constraint, a pending approval, an
idempotency key. Those facts are what compaction must not lose.

Step counts follow Chapter 10 (median 7.4, p95 19, cap 24). Most runs
are plain changes with small tool results; disruption runs, more
likely the longer a run goes, carry multi-carrier searches of several
thousand tokens each, and those are the runs whose context grows.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from common.rand import seeded

from .slots import Item

STEPS_MU, STEPS_SIGMA, STEP_CAP = math.log(7.6), 0.58, 24
N_RUNS = 2_000
BUCKETS = ((1, 4), (5, 8), (9, 12), (13, 16), (17, 24))

CONSTRAINTS = (
    "no overnight departures; traveling with two children",
    "must land before 6 p.m.; connecting to a cruise",
    "no connections through a second carrier",
    "keep the aisle seats already assigned",
    "do not change the return leg",
)


@dataclass(frozen=True)
class Fact:
    key: str
    kind: str          # constraint, approval, amount, idem
    text: str
    step: int


@dataclass
class Step:
    n: int
    history: list[Item]
    retrieved: list[Item] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    needs: tuple[str, ...] = ()       # fact keys this step relies on


@dataclass
class Run:
    run_id: str
    itinerary: str
    disruption: bool
    task: list[Item]
    memory: list[Item]
    steps: list[Step]

    @property
    def length(self) -> int:
        return len(self.steps)

    def facts(self) -> list[Fact]:
        return [f for s in self.steps for f in s.facts]


def bucket(steps: int) -> str:
    for lo, hi in BUCKETS:
        if lo <= steps <= hi:
            return f"{lo}-{hi}"
    raise ValueError(steps)


def _steps(r) -> int:
    n = round(math.exp(r.gauss(STEPS_MU, STEPS_SIGMA)))
    return max(2, min(STEP_CAP, n))


def _tool_tokens(r, disruption: bool) -> int:
    x = r.random()
    if disruption:
        if x < 0.30:
            return r.randint(150, 700)
        if x < 0.60:
            return r.randint(2_000, 6_000)
        return r.randint(6_000, 14_000)
    if x < 0.90:
        return r.randint(150, 700)
    return r.randint(1_200, 3_000)


def make_run(seed: int, i: int) -> Run:
    r = seeded(seed, "context-run", str(i))
    n = _steps(r)
    p_dis = 0.04 if n <= 8 else 0.30 if n <= 16 else 0.85
    dis = r.random() < p_dis
    itin = f"LTG-{5_300_000 + r.randint(0, 99_999)}"
    rid = f"run-{i:04d}"
    task = [Item("task", f"{itin}:packet", r.randint(400, 700)),
            Item("task", f"{itin}:msg1", r.randint(60, 220))]
    memory = [Item("memory", f"{itin}:mem", r.randint(120, 300))] \
        if r.random() < 0.6 else []
    steps: list[Step] = []
    c_step = 1 if r.random() < 0.5 else 2
    has_c = r.random() < 0.7
    has_a = n >= 4 and r.random() < 0.40
    a_step = r.randint(2, max(2, n - 2)) if has_a else -1
    amount = r.randint(9_000, 150_000) / 100
    for k in range(1, n + 1):
        out = max(20, round(math.exp(r.gauss(5.03, 0.5))))
        hist = [Item("history", f"{rid}:s{k}:turn", out),
                Item("history", f"{rid}:s{k}:tool",
                     _tool_tokens(r, dis))]
        if r.random() < 0.3:
            hist.append(Item("history", f"{rid}:s{k}:cust",
                             r.randint(40, 160)))
        ret = []
        if r.random() < 0.35:
            for j in range(r.randint(1, 3)):
                ret.append(Item("retrieved", f"{rid}:s{k}:p{j}",
                                r.randint(300, 900), rank=j))
        facts = []
        if has_c and k == c_step:
            facts.append(Fact(f"{rid}:constraint", "constraint",
                              r.choice(CONSTRAINTS), k))
        if k == a_step:
            apr = f"APR-{r.randint(10_000, 99_999)}"
            facts += [Fact(f"{rid}:approval", "approval",
                           f"{apr} pending for refund on {itin}", k),
                      Fact(f"{rid}:amount", "amount",
                           f"${amount:,.2f}", k),
                      Fact(f"{rid}:idem", "idem",
                           f"idem-{itin}-rf1", k)]
        needs = ()
        if k == n or (has_a and k > a_step and r.random() < 0.3):
            needs = tuple(f.key for s in steps for f in s.facts) + \
                tuple(f.key for f in facts)
        steps.append(Step(k, hist, ret, facts, needs))
    return Run(rid, itin, dis, task, memory, steps)


def make_runs(seed: int = 21, n: int = N_RUNS) -> list[Run]:
    return [make_run(seed, i) for i in range(n)]


def opening_run() -> Run:
    """The April run in the chapter's opening: 22 steps, a multi-leg
    disruption, a constraint at step 2 that a proposal at step 20
    broke. Sizes are fixed so the peak is the same on every machine."""
    itin = "LTG-5318806"
    rid = "R-0423-0117"
    task = [Item("task", f"{itin}:packet", 690),
            Item("task", f"{itin}:msg1", 184)]
    memory = [Item("memory", f"{itin}:mem", 210)]
    tools = (420, 6_840, 380, 8_920, 510, 9_210, 2_960, 440, 9_480,
             3_910, 520, 9_960, 4_120, 390, 9_760, 3_260, 610, 9_840,
             4_430, 560, 9_330, 6_442)
    turns = (160, 210, 140, 230, 150, 190, 170, 160, 220, 180, 150,
             240, 170, 150, 210, 180, 160, 230, 190, 260, 200, 170)
    steps = []
    for k, (tool, turn) in enumerate(zip(tools, turns), 1):
        hist = [Item("history", f"{rid}:s{k}:turn", turn),
                Item("history", f"{rid}:s{k}:tool", tool)]
        facts = []
        if k == 2:
            hist.append(Item("history", f"{rid}:s2:cust", 64))
            facts = [Fact(f"{rid}:constraint", "constraint",
                          CONSTRAINTS[0], 2)]
        needs = (f"{rid}:constraint",) if k == 20 else ()
        steps.append(Step(k, hist, [], facts, needs))
    return Run(rid, itin, True, task, memory, steps)
