"""One scenario of the storm day, run minute by minute.

A scenario says when each control acted: the order the desk worked
in and when it changed, the approvers seated through the day, when
the fleet day's emergency release came and how much, when the second
kill-switch tier held the low-urgency kinds and when it let them go,
and when the signed surge rule for involuntary refunds was active.

`as_run` is the day as Ben Carter's incident record has it. The
others are what the review compared it with.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from functools import lru_cache
from statistics import median

from . import budget as B
from .day import CLOSE, DAY_END, DAY_START, generate
from .desk import Desk

# Approvers seated on the refund approver desks and the agent desk.
SEATED_AS_RUN = ((DAY_START, 18), (11 * 60, 20), (11 * 60 + 30, 22),
                 (12 * 60, 40), (12 * 60 + 30, 42), (13 * 60, 46),
                 (13 * 60 + 30, 50), (14 * 60, 54), (14 * 60 + 30, 58),
                 (15 * 60, 62), (17 * 60, 16), (21 * 60 + 40, 17),
                 (23 * 60, 18))
# Marcus Bell's rota change after the review: on a declared weather
# incident the day shift holds to 7 p.m. and half of it to 9 p.m.
SEATED_ROTA = tuple(x for x in SEATED_AS_RUN if x[0] < 17 * 60) + (
    (19 * 60, 30), (21 * 60, 17), (23 * 60, 18))
LOW_URGENCY = ("refund_vol", "credit")
CLEAR_DEPTH = 50          # Chapter 8's cap: an ordinary desk again
SWEEP_PER_MIN = 400       # the engine re-deciding queued refunds
DECLINE = 0.03            # cards a person declines
OLDEST_ALERT = 60         # Marcus's objective: no card waits an hour
RUN_PAST = 12 * 60        # run into Friday morning for the held work

# Probability that an effect taken on the day is verified by a
# reconciler that did not act. Storm rebookings are lower because
# carriers canceled some of the new flights again that evening.
P_VERIFIED = {"rebook": 0.9855, "rebook_card": 0.9855,
              "cancel": 0.998, "voucher": 0.996, "refund_inv": 0.998,
              "refund_vol": 0.998, "credit": 0.999,
              "surge": 0.9975}


def t(h: int, m: int = 0) -> int:
    return h * 60 + m


@dataclass(frozen=True)
class Scenario:
    name: str
    order: str = "newest"
    switch_at: int | None = t(14, 2)
    switch_to: str = "departure"
    seated: tuple = SEATED_AS_RUN
    declare_at: int = t(11, 40)
    emergency_at: int | None = t(12, 48)
    emergency_usd: float = 2_500.00
    tier2_at: int | None = t(14, 41)
    tier2_release_at: int | None = t(22, 52)
    surge_at: int | None = t(15, 5)
    surge_hours: float = 12.0
    surge_limit_usd: float = 500.00
    fleet_day_usd: float = B.FLEET_DAY_USD


SCENARIOS = {
    "as-run": Scenario("as-run"),
    "no-priority": Scenario("no-priority", switch_at=None),
    "no-emergency": Scenario("no-emergency", emergency_at=None),
    "fare": Scenario("fare", switch_to="fare"),
    "widen-1000": Scenario("widen-1000", surge_limit_usd=1_000.00),
    "no-tier2": Scenario("no-tier2", tier2_at=None),
    "redesigned": Scenario(
        "redesigned", order="departure", switch_at=None,
        emergency_at=t(11, 40), tier2_at=t(11, 40), surge_at=t(12, 10)),
}
SCENARIOS["redesigned-rota"] = replace(
    SCENARIOS["redesigned"], name="redesigned-rota", seated=SEATED_ROTA)


@dataclass
class Result:
    scenario: Scenario
    changes: int
    storm_changes: int
    depth: list = field(default_factory=list)       # per minute
    latency: list = field(default_factory=list)     # (minute, median)
    peak_depth: int = 0
    peak_at: int = 0
    oldest_at_peak: float = 0.0
    peak_latency: float = 0.0
    peak_latency_at: int = 0
    cleared_at: int | None = None
    paged_at: float | None = None
    budget_spent_at: float | None = None
    model_usd: float = 0.0
    to_people: int = 0
    voucher_spent_at: float | None = None
    voucher_to_people: int = 0
    held: int = 0
    held_done_at: int | None = None
    oldest_alert_at: int | None = None
    inflow: dict = field(default_factory=dict)   # minute: cards added
    oldest: list = field(default_factory=list)   # (minute, oldest card)
    missed: int = 0
    missed_by_peak: int = 0
    person_cards: int = 0
    person_minutes: float = 0.0
    surge_cards: int = 0
    surge_usd: float = 0.0
    surge_max_usd: float = 0.0
    agent_effects: int = 0
    effects: int = 0
    verified: float = 0.0
    fleet_limit: float = 0.0

    @property
    def verified_rate(self) -> float:
        failed = self.missed
        return self.verified / (self.effects + failed)

    @property
    def hours_to_clear(self) -> float | None:
        if self.cleared_at is None:
            return None
        return (self.cleared_at - self.scenario.declare_at) / 60


def _surge_ok(s: Scenario, now: float):
    if s.surge_at is None:
        return None
    end = s.surge_at + s.surge_hours * 60
    if not s.surge_at <= now < end:
        return None
    return lambda c: (c.kind == "refund_inv"
                      and c.amount <= s.surge_limit_usd)


def _seated(s: Scenario, now: float) -> float:
    n = 0
    for at, k in s.seated:
        if now >= at:
            n = k
    return n


def run(s: Scenario | str = "as-run", seed: int = 2026) -> Result:
    if isinstance(s, str):
        s = SCENARIOS[s]
    return _run(s, seed)


@lru_cache(maxsize=None)
def _run(s: Scenario, seed: int) -> Result:
    changes = generate(seed)
    r = Result(s, len(changes),
               sum(1 for c in changes if CLOSE <= c.t < 17 * 60))
    fleet = B.FleetDay(limit=s.fleet_day_usd)
    vouchers = B.VoucherDay()
    desk = Desk(order=s.order)
    by_minute: dict[int, list] = {}
    for c in changes:
        by_minute.setdefault(int(c.t), []).append(c)
    tier2 = False
    effects: dict[str, int] = {}
    decline_n = 0

    def effect(kind: str, n: int = 1) -> None:
        effects[kind] = effects.get(kind, 0) + n

    held: list = []
    for now in range(DAY_START, DAY_END + RUN_PAST):
        desk.tick(now)
        if s.emergency_at is not None and now == s.emergency_at:
            fleet.release(now, s.emergency_usd, "Sarah Whitfield")
        if s.switch_at is not None and now == s.switch_at:
            desk.reorder(s.switch_to)
        if s.tier2_at is not None and now == s.tier2_at:
            tier2 = True
            held += desk.pull(LOW_URGENCY)
        if s.tier2_release_at is not None and now == s.tier2_release_at:
            tier2 = False
            r.held = len(held)
            for c in held:
                desk.add(c)
            held = []
        surge = _surge_ok(s, now)
        storm = CLOSE <= now
        for c in by_minute.get(now, []):
            if c.source == "chat":
                usd = B.TASK_USD if storm else B.CALM_TASK_USD
                if not fleet.admit(now, usd):
                    r.to_people += 1
                    continue
            if c.kind in ("rebook", "cancel"):
                effect(c.kind)
                r.agent_effects += 1
            elif c.kind == "voucher":
                if vouchers.take(now, c.amount):
                    effect("voucher")
                    r.agent_effects += 1
                else:
                    r.voucher_to_people += 1
            elif tier2 and c.kind in LOW_URGENCY:
                held.append(c)
            elif surge is not None and surge(c):
                r.surge_cards += 1
                r.surge_usd += c.amount
                r.surge_max_usd = max(r.surge_max_usd, c.amount)
                effect("surge")
                r.agent_effects += 1
            else:
                desk.add(c)
                r.inflow[now] = r.inflow.get(now, 0) + 1
        if surge is not None:
            before = len(desk.decided)
            desk.sweep(now, surge, SWEEP_PER_MIN)
            for d in desk.decided[before:]:
                r.surge_cards += 1
                r.surge_usd += d.amount
                r.surge_max_usd = max(r.surge_max_usd, d.amount)
                effect("surge")
                r.agent_effects += 1
        missed_now = desk.expire(now)
        r.missed += missed_now
        before = len(desk.decided)
        desk.work(now, _seated(s, now))
        for d in desk.decided[before:]:
            decline_n += 1
            if decline_n % round(1 / DECLINE) == 0:
                continue                      # declined: no effect
            effect(d.kind)
        r.depth.append((now, desk.depth))
        if r.oldest_alert_at is None and desk.oldest(now) > OLDEST_ALERT:
            r.oldest_alert_at = now
        released = (s.tier2_release_at is not None
                    and now >= s.tier2_release_at)
        if desk.depth > r.peak_depth and not released:
            r.peak_depth, r.peak_at = desk.depth, now
            r.oldest_at_peak = desk.oldest(now)
            r.missed_by_peak = r.missed
        if now % 10 == 0:
            r.oldest.append((now, desk.oldest(now)))
            lat = desk.latency(now)
            r.latency.append((now, lat))
            if lat > r.peak_latency:
                r.peak_latency, r.peak_latency_at = lat, now
        if (r.cleared_at is None and r.peak_depth > CLEAR_DEPTH * 2
                and now > r.peak_at and desk.depth < CLEAR_DEPTH):
            r.cleared_at = now
        if (r.held and r.held_done_at is None and not tier2
                and desk.depth == 0):
            r.held_done_at = now
    r.paged_at, r.budget_spent_at = fleet.paged_at, fleet.spent_at
    r.model_usd, r.fleet_limit = fleet.spent, fleet.limit
    r.voucher_spent_at = vouchers.spent_at
    r.person_cards = sum(1 for d in desk.decided if d.by == "person")
    r.person_minutes = desk.person_minutes
    r.effects = sum(effects.values())
    r.verified = sum(P_VERIFIED[k] * n for k, n in effects.items())
    return r


def depth_at(r: Result, minute: int) -> int:
    for m, d in r.depth:
        if m == minute:
            return d
    return 0


def median_wait(r: Result) -> float:
    return median(w for _, w in r.latency if w)


def variant(name: str, **kw) -> Scenario:
    return replace(SCENARIOS["as-run"], name=name, **kw)


def latency_while_newest(r: Result) -> float:
    """The dashboard's highest reading while the desk still worked
    newest first (the default, before the switch)."""
    end = r.scenario.switch_at or r.peak_at
    vals = [v for m, v in r.latency
            if r.scenario.declare_at - 30 <= m <= end + 20]
    return max(vals, default=0.0)


def latency_after(r: Result, lo: int, hi: int) -> float:
    return max((v for m, v in r.latency if lo <= m <= hi), default=0.0)


def latency_at(r: Result, minute: int) -> float:
    return dict(r.latency).get(minute, 0.0)
