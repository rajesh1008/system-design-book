"""Chapter 27 lab: one agent against orchestrator-worker, the stick
across workers, the relay baton, hierarchy depth, voting and debate,
and the topology card.

    python3 -m topology.demo                     # every part, seed 27
    python3 -m topology.demo --part compare
    python3 -m topology.demo --inject shared     # the June 16 design
    python3 -m topology.demo --part compare --third-worker
    python3 -m topology.demo --part compare --brief-tokens 600
    python3 -m topology.demo --part vote --rho 0
"""
from __future__ import annotations

import argparse
import sys

from common.text import emit

from . import card, compare, handoff, hierarchy, lock, vote
from .tasks import TYPES, label

PARTS = ("compare", "routed", "lock", "handoff", "hierarchy", "vote",
         "card")
SHORT = {"voluntary rebooking": "voluntary rebook",
         "involuntary rebooking": "involuntary rebook",
         "accept schedule change": "accept sched. change"}
RESULT = {"single": "single", "orchestrator": "orch.",
          "tie-single": "tie, single", "tie-orchestrator": "tie, orch."}


def part_compare(seed, call_cap=None):
    res = compare.compare(seed, call_cap=call_cap)
    t = compare.totals(res)
    emit(f"golden set: 1,200 cases x {compare.REPEATS} runs a topology")
    emit("  type                  single  orch.   diff  result      tok x")
    for kind, r in res.items():
        name = SHORT.get(label(kind), label(kind))
        emit(f"  {name:<20} {100 * r.single_ok / r.n:6.1f}% "
             f"{100 * r.ow_ok / r.n:5.1f}% {100 * r.diff:+5.1f}  "
             f"{RESULT[r.winner]:<11} {r.ow_tokens / r.single_tokens:4.2f}")
    emit(f"  all types            {100 * t['single_ok']:6.2f}% "
         f"{100 * t['ow_ok']:5.2f}%")
    emit(f"one agent wins {t['single_wins']} of 12 ({t['single_clear']} "
         f"clear, {t['ties']} ties on tokens); orchestrator "
         f"{t['ow_wins']}")
    emit(f"tokens a task: one agent {t['single_tokens_per_task']:,.0f}, "
         f"orchestrator {t['ow_tokens_per_task']:,.0f} "
         f"({t['token_ratio']:.2f}x)")
    emit(f"coordination share of orchestrator tokens: "
         f"{100 * t['coordination_share']:.1f}%")
    stops = sum(r.single_stops for r in res.values())
    cap = compare.CALL_CAP if call_cap is None else call_cap
    emit(f"one-agent runs stopped by the {cap}-call budget: {stops}")
    rebook = [r for r in res.values() if TYPES[r.kind][4]]
    s95 = compare.p95([x for r in rebook for x in r.single_secs])
    o95 = compare.p95([x for r in rebook for x in r.ow_secs])
    emit(f"p95 model time, rebooking types: one agent {s95:.0f} s, "
         f"orchestrator {o95:.0f} s")


def part_routed(seed):
    compare.compare(seed)
    r = compare.routed()
    emit("by legs, all types")
    emit("  legs   runs  one agent  orch.   tok x")
    for name, b in (("1-2", r["few"]), ("3+", r["many"])):
        emit(f"  {name:<4} {b.n:>6,}  {100 * b.single_ok / b.n:8.1f}% "
             f"{100 * b.ow_ok / b.n:6.1f}%  "
             f"{b.ow_tokens / b.single_tokens:5.2f}")
    emit("route 3+ legs to orchestrator-worker, the rest to one agent:")
    emit(f"  verified {100 * r['routed_ok']:.2f}% (all one agent "
         f"{100 * r['all_single_ok']:.2f}%, all orch. "
         f"{100 * r['all_ow_ok']:.2f}%)")
    emit(f"  tokens {r['routed_token_ratio']:.2f}x all one agent")


def part_lock(seed, modes=("none", "shared", "stick")):
    emit("two leg workers, one itinerary, 5,000 runs")
    emit("  mode     overlaps  conflicts  waited  stood down  late refused")
    for m in modes:
        x = lock.trial(m, seed=seed)
        emit(f"  {m:<8} {x.overlaps:>8,}  {x.conflicts:>9,}  "
             f"{x.waited:>6,}  {x.stood_down:>10,}  {x.late_refused:>12}")
        if m == "stick" and x.waited:
            emit(f"  waiting added {x.extra_seconds:,.0f} s in all, "
                 f"{x.extra_seconds / x.waited:.1f} s a wait")


def part_handoff(seed):
    emit("1,000 handoffs; 3% acks lost, 1% receivers fail first")
    emit("  design            orphaned  two owners  unknown  re-offered")
    for d in ("fire-and-forget", "ack-and-retry", "baton"):
        x = handoff.trial(d, seed=seed)
        emit(f"  {d:<16} {x.orphaned:>9}  {x.two_owners:>10}  "
             f"{x.unknown:>7}  {x.reoffered:>10}")


def part_hierarchy(seed):
    emit("eight facts, 1,200 cases, by levels below the lead")
    emit("  depth  free summary  pinned list  added s  brief tokens")
    for d in (1, 2, 3):
        f = hierarchy.trial(d, "free", seed=seed)
        p = hierarchy.trial(d, "pinned", seed=seed)
        emit(f"  {d:>5}  {f.intact:>12,}  {p.intact:>11,}  "
             f"{f.seconds_added:>7.1f}  {f.brief_tokens:>12,}")


def part_vote(seed, rho=None):
    rows = vote.table(seed, rho)
    base = rows[0].tokens
    emit(f"eligibility, 24 tasks x {vote.REPEATS} runs, correlation "
         f"{vote.RHO if rho is None else rho}")
    emit("  design    correct  desk  wrong  calls  tokens x")
    for x in rows:
        emit(f"  {x.design:<8} {100 * x.success:7.1f}%  {x.desk:>4}  "
             f"{x.wrong:>5}  {x.calls:>5,}  {x.tokens / base:8.2f}")


def part_card(seed, lock_mode="stick"):
    rows = card.rows(seed, lock_mode)
    if lock_mode != "stick":
        emit(f"INJECTED: gateway checks the token only ({lock_mode})")
    emit("topology card, as of June 23, 2026 (lab replay)")
    for r in rows:
        mark = "*" if r.name == card.HIGHLIGHT else " "
        emit(f"{mark} {r.name:<23} {r.value:<33} "
             f"{'ok' if r.ok else 'FAIL'}")
    failed = [r.name for r in rows if not r.ok]
    if failed:
        emit("CHECK FAILED: " + ", ".join(failed))
        return 1
    emit("check passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=27)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=("shared",))
    ap.add_argument("--call-cap", type=int)
    ap.add_argument("--brief-tokens", type=int)
    ap.add_argument("--third-worker", action="store_true",
                    help="brief a hotel worker on every rebooking too")
    ap.add_argument("--rho", type=float)
    a = ap.parse_args(argv)
    if a.brief_tokens is not None:
        compare.BRIEF_TOKENS = a.brief_tokens
    if a.third_worker:
        for k, v in TYPES.items():
            if v[4]:
                TYPES[k] = v[:3] + (v[3] + ("hotel",),) + v[4:]
    if a.inject:
        return part_card(a.seed, a.inject)
    parts = [a.part] if a.part else list(PARTS)
    code = 0
    for i, p in enumerate(parts):
        if i:
            emit()
        emit(f"-- {p} --")
        if p == "compare":
            part_compare(a.seed, a.call_cap)
        elif p == "routed":
            part_routed(a.seed)
        elif p == "lock":
            part_lock(a.seed)
        elif p == "handoff":
            part_handoff(a.seed)
        elif p == "hierarchy":
            part_hierarchy(a.seed)
        elif p == "vote":
            part_vote(a.seed, a.rho)
        elif p == "card":
            code = part_card(a.seed)
    return code


if __name__ == "__main__":
    sys.exit(main())
