"""Chapter 18 lab: the cost model and budget enforcement.

Offline and deterministic: the recorded pilot tasks from Chapter 10,
priced with serving.prices; no model call and no key. All amounts are
US dollars. Lakeshore figures are illustrative.

    python3 -m cost.demo --seed 18
    python3 -m cost.demo --part budget --no-budget
"""
from __future__ import annotations

import argparse
from dataclasses import replace

from common.text import emit

from . import budget as B
from . import cache as C
from . import forecast as F
from . import levers as LV
from .unit import APRIL, MAY, LINES, by_kind, ladder, month_cost

PARTS = ("unit", "ladder", "kinds", "levers", "cache", "semantic", "budget",
         "race", "month", "surge", "forecast", "card")
BASELINE = 37.94


def part_unit(seed: int, handoff: float | None) -> None:
    for m in (APRIL, MAY):
        if handoff is not None:
            m = replace(m, handoff=handoff)
        c = month_cost(m, seed)
        emit(f"{m.name}: {c['verified']:,} verified outcomes,"
             f" {c['executed']:,} executed, {c['attempts']:,} attempts")
        for k in LINES:
            v = c["lines"][k]
            emit(f"  {k:<18}{v:>10,.0f}{v / c['verified']:>9.3f}"
                 f"{v / c['total']:>8.1%}")
        emit(f"  {'total':<18}{c['total']:>10,.0f}"
             f"{c['per_outcome']:>9.3f}")
        emit(f"  people minutes {c['people_min']:,.0f};"
             f" cost per verified outcome ${c['per_outcome']:.2f}")
    emit(f"  baseline blend ${BASELINE:.2f}; May is"
         f" {month_cost(MAY, seed)['per_outcome'] / BASELINE:.1%}"
         f" of it")


def part_ladder(seed: int) -> None:
    emit("May 2026, the same spend divided six ways")
    for name, v in ladder(MAY, seed):
        emit(f"  {name:<36}{'$' + format(v, '.4f'):>10}")


def part_kinds(seed: int) -> None:
    emit("May 2026 by kind of change ($ per verified outcome)")
    emit(f"  {'kind':<8}{'outcomes':>9}{'model':>7}{'tools':>7}"
         f"{'platf.':>7}{'verif.':>7}{'people':>8}{'total':>7}")
    for k, v in by_kind(MAY, seed).items():
        n, ln = v["verified"], v["lines"]
        people = (ln["review labor"] + ln["rework"]
                  + ln["repeat contacts"])
        emit(f"  {k:<8}{n:>9,.0f}{ln['model tokens'] / n:>7.3f}"
             f"{ln['tools and fees'] / n:>7.3f}"
             f"{ln['platform'] / n:>7.3f}"
             f"{ln['verification'] / n:>7.3f}{people / n:>8.3f}"
             f"{v['per_outcome']:>7.2f}")


def part_levers(seed: int) -> None:
    rows = LV.sensitivity(MAY, seed)
    emit("levers, one at a time from the May design")
    emit(f"  {'lever':<10}{'worse':<14}{'better':<13}"
         f"{'model/attempt':>15}{'$/outcome':>12}")
    base = rows[0]
    emit(f"  {'May':<37}{base['model_base']:>15.4f}"
         f"{base['outcome_base']:>12.3f}")
    for r in rows:
        emit(f"  {r['lever']:<10}{r['worse']:<14}{r['better']:<13}"
             f"{r['model_worse']:>7.4f}-{r['model_better']:.4f}"
             f"{r['outcome_worse']:>7.3f}-{r['outcome_better']:.3f}")
    emit("hand-off rate, the lever not on the token bill")
    for rate, v in LV.handoff_lever(MAY, seed):
        emit(f"  {rate:>4.0%} of attempts handed off: ${v:.3f}")
    p = LV.price_cut(MAY, 0.5, seed)
    emit(f"model prices cut 50%: ${p['before']:.3f} -> ${p['after']:.3f}"
         f" a verified outcome")


def part_cache(seed: int) -> None:
    r = C.response_cache(seed=seed)
    emit("response cache, fare rules keyed by carrier, fare basis,"
         " policy")
    emit(f"  {r['calls']:,} lookups, {r['entries']:,} entries,"
         f" hit {r['hit_rate']:.1%}")


def part_semantic(seed: int, threshold: float) -> None:
    r = C.semantic(threshold, seed=seed)
    emit(f"semantic cache on refund requests, threshold {threshold:.2f}")
    emit(f"  {r['asks']} requests, {r['served']} served from cache")
    emit(f"  served from another customer's case: {r['other_customer']}")
    emit(f"    different fare class {r['fare_diff']},"
         f" different date {r['date_diff']}")
    emit(f"    wrong refund decision: {r['wrong']}")
    if r["example"]:
        a, b, s = r["example"]
        emit(f"  e.g. similarity {s:.3f}: asked {a.fare},"
             f" May {a.day} ({a.answer});")
        emit(f"       served {b.customer}'s {b.fare}, May {b.day}"
             f" ({b.answer})")
    p = C.policy_only(seed=seed)
    emit("policy answers only, keyed by policy version")
    emit(f"  {p['policy_answers_served']} served,"
         f" {p['entries']} entries,"
         f" from another customer's case: {p['other_customer']}")


def part_budget(no_budget: bool, task_usd: float) -> None:
    worst, derived = B.derive_task_usd()
    emit(f"task budget: costliest recorded task under April design"
         f" ${worst:.2f}")
    emit(f"  x 1.3, up to the next quarter: ${derived:.2f}")
    r = B.replay_runaway()
    emit("April 18 runaway, as run (step cap in the loop's memory)")
    emit(f"  {r.wakes_run} wakes, {r.calls} calls, ${r.spent:.2f}")
    if no_budget:
        r = B.replay_runaway(loop_cap=False)
        emit("no step cap and no spend budget")
        emit(f"  {r.wakes_run} wakes, {r.calls} calls, ${r.spent:.2f}")
        limits = B.Limits(task_usd=task_usd)
    else:
        limits = B.Limits(task_usd=task_usd)
        e = B.Enforcer(limits)
        r = B.replay_runaway(e)
        emit(f"with the enforcer (task budget ${task_usd:.2f})")
        emit(f"  stopped on wake {r.stopped_at[0]}, call"
             f" {r.stopped_at[1]}: {r.stop} budget")
        emit(f"  {r.calls} calls, ${r.spent:.2f}; later wakes refused:"
             f" {r.refused_wakes}")
    fails = B.check_runaway(r, limits)
    emit(f"budget test: {'FAIL' if fails else 'PASS'}")
    for f in fails:
        emit(f"  {f}")


def part_race() -> None:
    emit("two calls, one task, $0.20 left, $0.15 worst case each")
    for reserve in (False, True):
        r = B.race(reserve=reserve)
        how = "reserve first" if reserve else "check, then spend"
        emit(f"  {how:<18} admitted {r['admitted']},"
             f" spent ${r['spent']:.2f} of ${r['limit']:.2f}")


def part_month(seed: int, task_usd: float) -> None:
    r = B.replay_month(B.Limits(task_usd=task_usd), seed=seed)
    d = r["days"]
    emit(f"enforcer replay, May 2026: {r['tasks']:,} loop tasks,"
         f" {r['reservations']:,} calls")
    stops = ", ".join(f"{k} {v:,}" for k, v in r["stops"].items())
    emit(f"  stopped at a budget: {stops or 'none'}")
    emit(f"  rows over budget: {len(r['over'])}")
    emit(f"  costliest task ${r['max_task']:.2f};"
         f" busiest day ${max(d.values()):.2f}")
    emit(f"  month ${sum(d.values()):,.2f}; day alerts: {len(r['alerts'])}")


def part_surge(seed: int, surge: float, day_usd: float) -> None:
    r = B.replay_month(B.Limits(day_usd=day_usd), seed=seed,
                       day_scale={4: surge})
    emit(f"storm on Monday, May 4: {surge:.1f}x volume,"
         f" day budget ${day_usd:.0f}")
    emit(f"  May 4 spend ${r['days']['day:2026-05-04']:.2f};"
         f" alerts {len(r['alerts'])}")
    emit(f"  tasks sent to people at intake:"
         f" {r['stops'].get('intake', 0):,}")
    emit(f"  rows over budget: {len(r['over'])}")


def part_forecast(seed: int) -> None:
    emit("forecast written June 1, 2026 ($ per verified outcome)")
    emit(f"  {'month':<12}{'share':>6}{'low':>7}{'mid':>7}{'high':>7}"
         f"{'actual':>8}{'bill, mid':>12}")
    for r in F.forecast(seed):
        a = f"{r['actual']:.2f}" if r["actual"] else "-"
        emit(f"  {r['month'][:-5]:<12}{r['agent']:>6.0%}{r['low']:>7.2f}"
             f"{r['mid']:>7.2f}{r['high']:>7.2f}{a:>8}"
             f"{r['bill_mid']:>12,.0f}")
    emit("tokens per attempt drift, May volumes")
    for d, model, per in F.step_drift(seed):
        emit(f"  +{d:>3.0%}: model line ${model:,.0f},"
             f" ${per:.3f} a verified outcome")


def part_card(seed: int) -> None:
    c = month_cost(MAY, seed)
    r = B.replay_month(seed=seed)
    emit("economics card, May 2026")
    emit(f"  cost per verified outcome  ${c['per_outcome']:.2f}"
         f" against ${BASELINE:.2f}")
    emit("  budgets enforced           task, traveler-day, fleet-day")
    emit(f"  runs over budget           {len(r['over'])}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=18)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--threshold", type=float, default=0.92)
    ap.add_argument("--task-usd", type=float, default=1.00)
    ap.add_argument("--no-budget", action="store_true")
    ap.add_argument("--surge", type=float, default=3.0)
    ap.add_argument("--day-usd", type=float, default=120.0)
    ap.add_argument("--handoff", type=float)
    a = ap.parse_args()
    run = {"unit": lambda: part_unit(a.seed, a.handoff),
           "ladder": lambda: part_ladder(a.seed),
           "kinds": lambda: part_kinds(a.seed),
           "levers": lambda: part_levers(a.seed),
           "cache": lambda: part_cache(a.seed),
           "semantic": lambda: part_semantic(a.seed, a.threshold),
           "budget": lambda: part_budget(a.no_budget, a.task_usd),
           "race": part_race,
           "month": lambda: part_month(a.seed, a.task_usd),
           "surge": lambda: part_surge(a.seed, a.surge, a.day_usd),
           "forecast": lambda: part_forecast(a.seed),
           "card": lambda: part_card(a.seed)}
    for i, p in enumerate([a.part] if a.part else PARTS):
        if i:
            emit()
        run[p]()


if __name__ == "__main__":
    main()
