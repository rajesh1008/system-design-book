"""The loop-day scope: Chapter 18's enforcer, for work with no task.

Chapter 18's enforcer reserves on three scopes, the task, the
traveler's day and the fleet's day, and an unattended loop has no
task and no traveler in flight. This keeps the enforcer and changes
the scopes: a run of the loop takes the task's place, the loop's own
day takes the traveler's, and every unattended loop together shares
a loops-day envelope kept apart from the $120.00 fleet day that
customer tasks spend. Reserve the worst case, settle the real price,
refuse with a scope name; the loop hands off on a refusal.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from cost.budget import BudgetStop, Enforcer, Limits
from serving.prices import Bill


def loop_limits(loops_day_usd: float = 40.00,
                alert: float = 0.80) -> Limits:
    return Limits(task_usd=None, task_steps=None,
                  traveler_day_usd=None, day_usd=loops_day_usd,
                  alert=alert)


@dataclass
class LoopEnforcer(Enforcer):
    budgets: dict = field(default_factory=dict)   # loop -> budget

    @classmethod
    def for_specs(cls, *specs) -> "LoopEnforcer":
        b = {s["loop"]: s["budget"] for s in specs}
        day = max(x.get("loops_day_usd", 40.0) for x in b.values())
        alert = min(x.get("alert", 0.8) for x in b.values())
        return cls(limits=loop_limits(day, alert), budgets=b)

    def _scopes(self, task: str, traveler: str, day: str):
        b = self.budgets[traveler]
        return (("run", f"task:{traveler}/{task}", b["run_usd"]),
                ("loop-day", f"loop:{traveler}:{day}",
                 b["loop_day_usd"]),
                ("loops-day", f"day:{day}", self.limits.day_usd))

    def reserve(self, task: str, traveler: str, day: str,
                worst: float) -> int:
        cap = self.budgets[traveler]["run_steps"]
        row = self.store.row(f"task:{traveler}/{task}")
        if row["calls"] >= cap:
            self.log.append({"stop": "run-steps", "key": task,
                             "calls": row["calls"]})
            raise BudgetStop("run-steps", task, row["calls"], cap, 1)
        return super().reserve(task, traveler, day, worst)

    def settle(self, rid: int, actual: float) -> None:
        keys, _w = self._open[rid]
        super().settle(rid, actual)
        loop_key = keys[1]
        loop = loop_key.split(":")[1]
        b = self.budgets[loop]
        if self.store.row(loop_key)["spent"] >= \
                b.get("alert", 0.8) * b["loop_day_usd"] and not any(
                e.get("alert") == loop_key for e in self.log):
            self.log.append({"alert": loop_key})

    def over(self) -> list[str]:
        bad = []
        for key, r in self.store.rows.items():
            if key.startswith("day:"):
                limit = self.limits.day_usd
            elif key.startswith("loop:"):
                limit = self.budgets[key.split(":")[1]]["loop_day_usd"]
            else:
                continue
            if r["spent"] > limit + 1e-9:
                bad.append(key)
        return bad

    def runs_over(self, run_usd: dict) -> list[str]:
        """Runs whose settled spend passed their run budget."""
        return [k for k, r in self.store.rows.items()
                if k.startswith("task:") and "/" in k and
                r["spent"] > run_usd[k[5:].split("/")[0]] + 1e-9]


# The comparability call: both fares' rules and the watch, on mid.
JUDGE_IN, JUDGE_OUT, JUDGE_MAX = 9_000, 250, 512


def judge_usd() -> float:
    return Bill(uncached=JUDGE_IN, output=JUDGE_OUT).usd("mid")


def judge_worst() -> float:
    return Bill(uncached=JUDGE_IN, output=JUDGE_MAX).usd("mid")
