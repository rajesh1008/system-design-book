"""Budgets enforced outside the loop.

The enforcer sits in the control plane. The model gateway and the tool
gateway ask it for a reservation before every call, at the worst case
for that call; it checks every scope the call belongs to (the task,
the traveler's day, and the fleet's day) and either reserves against
all of them or refuses. After the call, the gateway settles the
reservation at the real price. The counters live in the run store, so
a run that sleeps, wakes, or resumes on another worker finds the
budget exactly where it left it.

The agent's loop never sees a counter. It sees a structured refusal
and does the one thing it is allowed to do with one: hand off.
"""
from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path

from common import seeded
from serving.prices import Bill

from .unit import MAY_LEVERS, Levers, calls_of, _tasks, sample, APRIL_LEVERS


@dataclass(frozen=True)
class Limits:
    task_usd: float | None = 1.00       # one task, all its wakes
    task_steps: int | None = 24         # model calls a task may make
    traveler_day_usd: float | None = 3.00
    day_usd: float | None = 120.00      # the fleet, one calendar day
    alert: float = 0.80                 # page the operator at 80%


def derive_task_usd(lv: Levers = APRIL_LEVERS, margin: float = 1.1,
                    step: float = 0.25) -> tuple[float, float]:
    """Task budget from the recorded tasks: the costliest task under
    the April design, plus a margin, rounded up to the next quarter."""
    worst = max(t.machine for t in sample(lv))
    return worst, math.ceil(worst * margin / step) * step


class BudgetStop(Exception):
    def __init__(self, scope: str, key: str, spent: float, limit: float,
                 worst: float):
        super().__init__(f"{scope} budget: {spent:.2f} + {worst:.2f} "
                         f"> {limit:.2f}")
        self.scope, self.key = scope, key
        self.spent, self.limit, self.worst = spent, limit, worst


class Store:
    """Stands in for the budget table in the run store. Rows survive a
    restart when a path is given, which is the property that matters."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.rows: dict[str, dict] = {}
        if path is not None and path.exists():
            self.rows = json.loads(path.read_text())

    def row(self, key: str) -> dict:
        return self.rows.setdefault(
            key, {"spent": 0.0, "reserved": 0.0, "calls": 0})

    def save(self) -> None:
        if self.path is not None:
            self.path.write_text(json.dumps(self.rows, sort_keys=True))


@dataclass
class Enforcer:
    limits: Limits = field(default_factory=Limits)
    store: Store = field(default_factory=Store)
    log: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _open: dict = field(default_factory=dict)
    _n: int = 0

    def _scopes(self, task: str, traveler: str, day: str):
        L = self.limits
        return (("task", f"task:{task}", L.task_usd),
                ("traveler-day", f"trav:{traveler}:{day}",
                 L.traveler_day_usd),
                ("day", f"day:{day}", L.day_usd))

    def reserve(self, task: str, traveler: str, day: str,
                worst: float) -> int:
        """Reserve the worst case on every scope, or refuse. Atomic:
        either all three counters move or none does."""
        with self._lock:
            scopes = self._scopes(task, traveler, day)
            trow = self.store.row(f"task:{task}")
            cap = self.limits.task_steps
            if cap is not None and trow["calls"] >= cap:
                self.log.append({"stop": "task-steps", "key": task,
                                 "calls": trow["calls"]})
                raise BudgetStop("task-steps", task, trow["calls"],
                                 cap, 1)
            for scope, key, limit in scopes:
                r = self.store.row(key)
                if limit is not None and \
                        r["spent"] + r["reserved"] + worst > limit:
                    self.log.append({"stop": scope, "key": key,
                                     "spent": r["spent"] + r["reserved"],
                                     "worst": worst, "limit": limit})
                    raise BudgetStop(scope, key,
                                     r["spent"] + r["reserved"],
                                     limit, worst)
            for _scope, key, _limit in scopes:
                self.store.row(key)["reserved"] += worst
            trow["calls"] += 1
            self._n += 1
            self._open[self._n] = ([k for _s, k, _l in scopes], worst)
            self.store.save()
            return self._n

    def settle(self, rid: int, actual: float) -> None:
        with self._lock:
            keys, worst = self._open.pop(rid)
            for key in keys:
                r = self.store.row(key)
                r["reserved"] -= worst
                r["spent"] += actual
            self.store.save()
            day_key = keys[-1]
            limit = self.limits.day_usd
            if limit and self.store.row(day_key)["spent"] >= \
                    self.limits.alert * limit and not any(
                    e.get("alert") == day_key for e in self.log):
                self.log.append({"alert": day_key})

    def over(self) -> list[str]:
        """Rows whose settled spend is above their limit."""
        L, bad = self.limits, []
        for key, r in self.store.rows.items():
            limit = (L.task_usd if key.startswith("task:") else
                     L.traveler_day_usd if key.startswith("trav:")
                     else L.day_usd)
            if limit is not None and r["spent"] > limit + 1e-9:
                bad.append(key)
        return bad


def worst_case(tokens_in: int, max_tokens: int, role: str) -> float:
    """No cache credit and every allowed output token: the most this
    call can cost."""
    return Bill(uncached=tokens_in, output=max_tokens).usd(role)


# --- the April 18 runaway ------------------------------------------------

@dataclass(frozen=True)
class Runaway:
    """A three-leg rebook and refund during a weather disruption on
    Saturday, April 18, 2026. The run waited on the schedule feed;
    every feed update woke it, and each wake re-planned the trip."""
    wakes: int = 11
    first_tokens: int = 40_000      # history at the first wake
    growth: int = 141               # tokens added per call
    out: int = 220
    max_tokens: int = 1_024
    hit: float = 0.092              # cold prefixes, April pilot
    role: str = "contract"          # all frontier in April
    loop_cap: int = 24              # the in-memory step cap


RUNAWAY = Runaway()


def _call_usd(r: Runaway, tokens_in: int) -> float:
    read = round(r.hit * tokens_in)
    written = round(min(1 - r.hit, 0.22) * tokens_in)
    return Bill(uncached=tokens_in - read - written, written=written,
                read=read, output=r.out).usd(r.role)


@dataclass
class RunResult:
    calls: int = 0
    spent: float = 0.0
    wakes_run: int = 0
    stop: str = ""
    stopped_at: tuple[int, int] | None = None
    refused_wakes: int = 0


def replay_runaway(enforcer: Enforcer | None = None,
                   r: Runaway = RUNAWAY, loop_cap: bool = True,
                   framework_limit: int = 50) -> RunResult:
    """Replay the run. With no enforcer, the April design: the step
    cap is a counter in the loop's memory and starts at zero on every
    wake. With an enforcer, every call asks the control plane first,
    and the counters persist across wakes."""
    res = RunResult()
    tokens = r.first_tokens
    for wake in range(1, r.wakes + 1):
        steps_this_wake = 0
        made_call = False
        while True:
            limit = r.loop_cap if loop_cap else framework_limit
            if enforcer is None and steps_this_wake >= limit:
                res.stop = res.stop or ("step cap, in loop" if loop_cap
                                        else "framework limit")
                break
            if enforcer is not None:
                try:
                    rid = enforcer.reserve(
                        "R-0418-0213", "TRV-55120", "2026-04-18",
                        worst_case(tokens, r.max_tokens, r.role))
                except BudgetStop as e:
                    if res.stopped_at is None:
                        res.stop = e.scope
                        res.stopped_at = (wake, steps_this_wake + 1)
                    elif not made_call:
                        res.refused_wakes += 1
                    break
            usd = _call_usd(r, tokens)
            if enforcer is not None:
                enforcer.settle(rid, usd)
            res.spent += usd
            res.calls += 1
            steps_this_wake += 1
            made_call = True
            tokens += r.growth
        res.wakes_run += made_call
    return res


def check_runaway(res: RunResult, limits: Limits) -> list[str]:
    """The budget test: the replayed runaway must stop at or under the
    task budget, and every wake after the stop must make no call."""
    fails = []
    if limits.task_usd is not None and res.spent > limits.task_usd:
        fails.append(f"spent ${res.spent:.2f} on one task, budget "
                     f"${limits.task_usd:.2f}")
    if res.stopped_at is None:
        fails.append("the run was never stopped by a budget")
    return fails


# --- two shoppers, one gift card ------------------------------------------

def race(limit: float = 1.00, spent: float = 0.80, worst: float = 0.15,
         reserve: bool = True) -> dict:
    """Two calls of one task arrive together with $0.20 left. Check-then-
    spend lets both through; a reservation lets one through."""
    if not reserve:
        # both read 0.80, both see room for 0.15, both spend
        admitted = sum(1 for _ in range(2) if spent + worst <= limit)
        return {"admitted": admitted, "spent": spent + admitted * worst,
                "limit": limit}
    e = Enforcer(Limits(task_usd=limit, task_steps=None,
                        traveler_day_usd=None, day_usd=None))
    e.store.row("task:T")["spent"] = spent
    ok = 0
    rids = []
    for _ in range(2):
        try:
            rids.append(e.reserve("T", "V", "D", worst))
            ok += 1
        except BudgetStop:
            pass
    for rid in rids:
        e.settle(rid, worst)
    return {"admitted": ok, "spent": e.store.row("task:T")["spent"],
            "limit": limit}


# --- a month of traffic through the enforcer -------------------------------

def replay_month(limits: Limits = Limits(), lv: Levers = MAY_LEVERS,
                 tasks: int = 33_040, days: int = 31, first_dow: int = 4,
                 travelers: int = 26_000, seed: int = 18,
                 max_tokens: int = 1_024,
                 day_scale: dict | None = None,
                 headroom: float = 0.05) -> dict:
    """Replay a month of loop tasks (agent plus assisted) drawn from
    the recorded pilot tasks, every call through the enforcer.
    first_dow 4 is a Friday (May 1, 2026)."""
    from corpus.traces import DAY_W
    from .unit import TIER_ROLE
    rng = seeded(seed, "cost-month", str(tasks))
    pool = _tasks()
    w = [DAY_W[(first_dow + d) % 7] * (day_scale or {}).get(d + 1, 1.0)
         for d in range(days)]
    e = Enforcer(limits)
    stops: dict[str, int] = {}
    spend: list[float] = []
    for n in range(tasks):
        d = rng.choices(range(days), w)[0]
        s = rng.choice(pool)
        trav = f"TRV-{rng.randrange(travelers):05d}"
        day, tid = f"2026-05-{d + 1:02d}", f"T{n:06d}"
        cost = 0.0
        if limits.day_usd is not None and e.store.row(f"day:{day}")[
                "spent"] >= limits.day_usd * (1 - headroom):
            # the intake gate (Chapter 8) stops admitting agent tasks;
            # tasks already running keep the headroom to finish
            stops["intake"] = stops.get("intake", 0) + 1
            spend.append(0.0)
            continue
        for _i, tier, tin, _tout, usd, fee in calls_of(s, lv, seed):
            try:
                rid = e.reserve(tid, trav, day,
                                worst_case(tin, max_tokens,
                                           TIER_ROLE[tier]) + fee)
            except BudgetStop as x:
                stops[x.scope] = stops.get(x.scope, 0) + 1
                break
            e.settle(rid, usd + fee)
            cost += usd + fee
        spend.append(cost)
    days_spend = {k: v["spent"] for k, v in e.store.rows.items()
                  if k.startswith("day:")}
    return {"tasks": tasks, "stops": stops, "over": e.over(),
            "max_task": max(spend), "days": days_spend,
            "alerts": [x["alert"] for x in e.log if "alert" in x],
            "reservations": e._n}
