"""Spend policies, enforced where every call passes: the model gateway.

A spend policy is a budget plus what happens at its edges. Lakeshore's
(DR-38.1, August 10, 2026) has three scopes for every loop, a run, the
loop's Chicago day, and the envelope all loops share, and two edges:
a page at half of a day's budget and a stop at all of it. A stop
refuses the loop's new calls for the rest of the Chicago day, resets
at midnight, and pages again.

The rule that matters most is the one for a call whose usage never
comes back. July's enforcer released the reservation, which settles
a timed-out call at nothing; the provider billed it in full. Here an
unknown settles at its worst case, and the nightly reconciler moves it
to the provider's figure by request id when the export lands.

This wraps `loops.budget.LoopEnforcer`, Chapter 28's enforcer, and
changes none of its arithmetic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from cost.budget import BudgetStop
from loops.budget import LoopEnforcer, loop_limits
from loops.spec import FARE_WATCH, WAIVER_WATCH


@dataclass(frozen=True)
class LoopBudget:
    loop: str
    run_usd: float
    run_steps: int
    loop_day_usd: float


@dataclass(frozen=True)
class SpendPolicy:
    name: str
    loops: tuple
    envelope_usd: float
    alert: float = 0.5
    unknown: str = "worst"        # or "release", July's rule

    def budget(self, loop: str) -> LoopBudget:
        return next(b for b in self.loops if b.loop == loop)


def _from_spec(spec: dict) -> LoopBudget:
    b = spec["budget"]
    return LoopBudget(spec["loop"], b["run_usd"], b["run_steps"],
                      b["loop_day_usd"])


JULY = SpendPolicy("July, as run", (_from_spec(WAIVER_WATCH),
                                    _from_spec(FARE_WATCH)),
                   envelope_usd=40.00, alert=0.80, unknown="release")
JULY_COUNTING = replace(JULY, name="July budgets, counting",
                        unknown="worst")
DR38 = SpendPolicy("DR-38.1", (
    LoopBudget("waiver-watch", 0.25, 12, 200.00),
    LoopBudget("fare-watch", 0.05, 6, 20.00)),
    envelope_usd=260.00, alert=0.50, unknown="worst")


class Refused(Exception):
    def __init__(self, scope: str, key: str):
        super().__init__(f"{scope} {key}")
        self.scope, self.key = scope, key


@dataclass
class Gateway:
    """The model gateway's spend check: one reservation per attempt,
    not per step, because the provider bills attempts."""
    policy: SpendPolicy
    events: list = field(default_factory=list)   # (time, what, key)
    counted: float = 0.0
    _stopped: dict = field(default_factory=dict)  # key -> day
    _paged: set = field(default_factory=set)

    def __post_init__(self):
        p = self.policy
        budgets = {b.loop: {"run_usd": b.run_usd,
                            "run_steps": b.run_steps,
                            "loop_day_usd": b.loop_day_usd,
                            "alert": p.alert} for b in p.loops}
        self.enf = LoopEnforcer(limits=loop_limits(p.envelope_usd,
                                                   p.alert),
                                budgets=budgets)

    def call(self, loop: str, run: str, t, worst: float,
             actual: float | None) -> float:
        """Reserve, let the call through, settle. Returns what the
        provider bills; raises Refused when a scope is spent."""
        day = t.date().isoformat()
        for key in (f"loop:{loop}:{day}", f"day:{day}"):
            if self._stopped.get(key) == day:
                raise Refused("stopped", key)
        try:
            rid = self.enf.reserve(run, loop, day, worst)
        except BudgetStop as e:
            if e.scope in ("loop-day", "loops-day"):
                self._stopped[e.key] = day
                self.events.append((t, "stop", e.key))
            raise Refused(e.scope, e.key) from None
        if actual is None and self.policy.unknown == "release":
            settled = 0.0
        elif actual is None:
            settled = worst
        else:
            settled = actual
        self.enf.settle(rid, settled)
        self.counted += settled
        self._page(t, loop, day)
        return worst if actual is None else actual

    def _page(self, t, loop: str, day: str) -> None:
        p = self.policy
        for key, limit in ((f"loop:{loop}:{day}",
                            p.budget(loop).loop_day_usd),
                           (f"day:{day}", p.envelope_usd)):
            spent = self.enf.store.row(key)["spent"]
            if key not in self._paged and spent >= p.alert * limit:
                self._paged.add(key)
                self.events.append((t, f"page {p.alert:.0%}", key))

    def spent(self, key: str) -> float:
        return self.enf.store.row(key)["spent"]

    def spent_by(self, loop: str) -> float:
        """What the gateway counted for one loop, every day."""
        return sum(r["spent"] for k, r in self.enf.store.rows.items()
                   if k.startswith(f"loop:{loop}:"))
