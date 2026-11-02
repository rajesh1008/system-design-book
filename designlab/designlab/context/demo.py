"""Chapter 21 lab: the context assembler, budgets, compaction,
isolation, rot, and the instruction file.

    python3 -m context.demo                  # every part, seed 21
    python3 -m context.demo --part compact
    python3 -m context.demo --inject unnoticed
    python3 -m context.demo --part card --compact-at 0.5
    python3 -m context.demo --part assemble --retrieved-first
    python3 -m context.demo --part compact --lengths
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from common.clock import FixedClock
from common.text import emit
from common.trail import TrailWriter, check_trail

from . import card, compact, drift, isolate, rot
from .assemble import assemble, reuse
from .runs import BUCKETS, bucket, make_runs, opening_run
from .slots import BUDGET, ORDER, Budget

PARTS = ("budget", "opening", "assemble", "compact", "verify",
         "isolate", "drift", "alarms", "card")
CHICAGO_MAY12 = "2026-05-12T09:00:00-05:00"
CHICAGO_MAY5 = "2026-05-05T08:00:00-05:00"


def production(runs, budget, trail=None, alarms_on=True, order=None):
    """May's design: isolation first, then pinned compaction, with the
    v9 instruction file."""
    return [compact.replay(isolate.isolate(r).run, "pinned", budget,
                           trail=trail, alarms_on=alarms_on, order=order,
                           release="v9")
            for r in runs]


def alarm_slot(alarm: str) -> str:
    """cap instructions 1,460 > 1,200 -> instructions;
    budget 52,310 > 48,000 (history 41,077) -> history."""
    if alarm.startswith("cap "):
        return alarm.split()[1]
    return alarm.rsplit("(", 1)[1].split()[0]


def alarms_by_slot(results) -> Counter:
    return Counter(alarm_slot(a) for x in results for a in x.alarms)


def part_budget(seed):
    pts = rot.harness(seed)
    k = rot.knee(pts)
    emit("context rot: 600 fixed pilot tasks, padded with real history")
    emit("  tokens   success")
    for L, ok, n in pts:
        emit(f"  {L:>7,}  {100 * ok / n:5.1f}%")
    emit(f"knee (two-line fit): {k:,} tokens")
    emit(f"budget a step, 20% below the knee: {rot.budget_from(k):,}")


def part_opening():
    run = opening_run()
    res = compact.replay(run, "none", alarms_on=False)
    emit(f"{run.run_id}, April 23: {run.length} steps, no budget")
    for n in (1, 2, 6, 12, 16, 20, 22):
        emit(f"  step {n:>2}: {res.tokens[n - 1]:>7,} tokens")
    emit(f"peak {res.peak:,} tokens; alarms raised: 0 (none existed)")
    emit("step 2, customer: " + run.steps[1].facts[0].text)
    emit("step 20 proposed an overnight departure; customer declined")


def part_assemble(retrieved_first=False):
    order = ORDER
    if retrieved_first:
        order = ("retrieved",) + tuple(s for s in ORDER
                                       if s != "retrieved")
    budget = Budget()
    run = next(r for r in make_runs() if r.length >= 18
               and r.steps[-1].retrieved and r.memory)
    res = compact.replay(isolate.isolate(run).run, "pinned", budget,
                         order=order, release="v9")
    a = res.last
    step = run.steps[-1]
    emit(f"{run.run_id}, step {step.n}, order: "
         + ("retrieved first" if retrieved_first else "stable first"))
    emit("  slot           tokens      cap")
    for s in order:
        cap = budget.caps.get(s)
        emit(f"  {s:<13} {a.by_slot.get(s, 0):>7,}  "
             f"{'-' if cap is None else f'{cap:,}':>7}")
    emit(f"  total         {a.tokens:>7,}   budget {budget.per_step:,}")
    emit("layout lint: clean" if not a.findings else
         f"layout lint: {len(a.findings)} finding")
    for f in a.findings:
        emit(f"  {f}")
    runs = make_runs()[:400]
    compare = [("stable first", ORDER)]
    if retrieved_first:
        compare.append(("retrieved first", order))
    for label, o in compare:
        res = production(runs, budget, order=o)
        share = sum(x.reused for x in res) / sum(x.sent for x in res)
        emit(f"prefix reuse, 400 runs, {label}: {100 * share:.1f}%")


def _by_bucket(results):
    out = []
    for lo, hi in BUCKETS:
        got = [x for x in results if lo <= x.length <= hi]
        ok = 100 * sum(x.success for x in got) / len(got)
        out.append((f"{lo}-{hi}", len(got), ok))
    return out


def part_compact(seed, budget, lengths=False):
    runs = make_runs(seed)
    emit(f"2,000 runs replayed, budget {budget.per_step:,}, "
         f"trigger {budget.trigger:,}")
    rows = {}
    for p in compact.POLICIES:
        rows[p] = [compact.replay(r, p, budget, seed) for r in runs]
    emit("success by run length (steps)")
    emit("  policy      " + " ".join(f"{lo}-{hi}".rjust(7)
                                     for lo, hi in BUCKETS))
    for p, res in rows.items():
        cells = " ".join(f"{ok:6.1f}%" for _, _, ok in _by_bucket(res))
        emit(f"  {p:<10} {cells}")
    emit("  runs       " + " ".join(f"{n:>7}" for _, n, _ in
                                    _by_bucket(rows['none'])))
    emit("facts lost, second approval cards, compactions")
    for p, res in rows.items():
        kinds = Counter(k for x in res for k in x.lost)
        emit(f"  {p:<9} runs {sum(bool(x.lost) for x in res):>3}"
             f"  cards {sum(x.second_card for x in res):>2}"
             f"  compactions {sum(x.compactions for x in res):>5,}")
        if kinds:
            emit("            " + ", ".join(
                f"{k} {v}" for k, v in sorted(kinds.items())))
    with_a = sum(any(f.kind == "approval" for f in r.facts())
                 for r in runs)
    emit(f"runs with a pending approval: {with_a}")
    if lengths:
        emit("peak context by run length, pinned (median)")
        for lo, hi in BUCKETS:
            got = sorted(x.peak for x in rows["pinned"]
                         if lo <= x.length <= hi)
            emit(f"  {lo:>2}-{hi:<2} {got[len(got) // 2]:>7,} tokens")


SUMMARY_FREE = ("Customer wants to move LTG-5318806 to an earlier "
                "flight. Refund of $412.80 discussed. Waiting on the "
                "customer to pick an option.")
SUMMARY_PINNED = ("Customer wants to move LTG-5318806. Pending: "
                  "APR-48213 for $412.80 under idem-LTG-5318806-rf1. "
                  "Constraint: no overnight departures.")
PINNED = ["APR-48213 pending for refund on LTG-5318806", "$412.80",
          "idem-LTG-5318806-rf1"]
TRAIL = ("LTG-5318806 APR-48213 $412.80 idem-LTG-5318806-rf1 "
         "FLT-904452")


def part_verify():
    for name, s in (("free-form", SUMMARY_FREE),
                    ("structured", SUMMARY_PINNED)):
        got = compact.verify_summary(s, PINNED, TRAIL)
        emit(f"verifier, {name} summary: " + ("pass" if not got
                                               else "FAIL"))
        for g in got:
            emit(f"  {g}")
    bad = SUMMARY_PINNED.replace("$412.80", "$421.80")
    emit("verifier, the structured summary with one digit changed:")
    for g in compact.verify_summary(bad, PINNED, TRAIL):
        emit(f"  {g}")


def part_isolate(seed, budget):
    runs = make_runs(seed)
    iso = [isolate.isolate(r) for r in runs]
    a = [compact.replay(r, "pinned", budget, seed) for r in runs]
    b = [compact.replay(i.run, "pinned", budget, seed) for i in iso]
    sa, sb = sum(x.sent for x in a), sum(x.sent for x in b)
    emit("isolation over 2,000 runs (pinned compaction in both)")
    emit(f"  lead tokens sent   {sa:>12,} -> {sb:>12,}"
         f"  ({100 * (sb - sa) / sa:+.1f}%)")
    emit(f"  to artifact store  {sum(i.to_store for i in iso):>12,}"
         f"  slices read back {sum(i.read_back for i in iso):,}")
    emit(f"  sub-agent calls    {sum(i.worker_calls for i in iso):>12,}"
         f"  tokens it read {sum(i.worker_tokens for i in iso):,}")
    emit(f"  runs compacted     {sum(bool(x.compactions) for x in a):>12,}"
         f" -> {sum(bool(x.compactions) for x in b):,}")
    emit(f"  successes          {sum(x.success for x in a):>12,}"
         f" -> {sum(x.success for x in b):,}")
    w = isolate.SubAgent("fare-rule-research")
    try:
        w.use("refund.issue")
    except isolate.NotPermitted as e:
        emit(f"  guard: {e}")


def part_drift():
    emit("instruction file by version")
    emit("  ver  date        lines  tokens stale contra no-own no-test")
    for v, d, n, t, f in drift.history():
        emit(f"  {v:<4} {d}  {n:>5}  {t:>6,}{len(f['stale']):>5}"
             f" {len(f['contradiction']):>6} {len(f['no owner']):>6}"
             f" {len(f['no test']):>7}")
    q = drift.lint(list(drift.QUOTED))
    emit("lint on the four quoted lines:")
    for k, v in q.items():
        emit(f"  {k:<14} {', '.join(v) or '-'}")


def part_alarms(seed, budget):
    runs = make_runs(seed)
    trail = TrailWriter(clock=FixedClock(CHICAGO_MAY5, 0.5))
    shadow = [compact.replay(r, "none", budget, seed, trail=trail,
                             release="v8") for r in runs]
    after = production(runs, budget)
    steps = sum(x.length for x in runs)
    a, b = alarms_by_slot(shadow), alarms_by_slot(after)
    emit(f"steps with an alarm, by slot ({steps:,} steps replayed)")
    emit("  slot           shadow (v8, no compaction)   May 31")
    for slot in sorted(set(a) | set(b), key=lambda k: -a[k]):
        emit(f"  {slot:<13} {a[slot]:>7,} ({100 * a[slot] / steps:4.1f}%)"
             f"            {b[slot]:>5,}")
    first = json.loads(trail.lines[0])
    emit(f"alarm log: {len(trail.lines):,} lines, first at {first['at']}")
    emit(f"  {first['alarm']}")


def part_card(seed, budget, inject=None):
    runs = make_runs(seed)
    before = [compact.replay(r, "none", budget, seed, alarms_on=False)
              for r in runs]
    trail = TrailWriter(clock=FixedClock(CHICAGO_MAY12, 0.5))
    if inject == "unnoticed":
        quiet = Budget(budget.per_step, compact_at=4.0)
        after = production(runs, quiet, trail, alarms_on=False)
        emit("INJECTED: compaction trigger 192,000 and alarms off")
    else:
        after = production(runs, budget, trail)
    v9 = drift.build("v9")
    f = drift.lint(v9)
    bad = len(f["stale"]) + len(f["contradiction"]) + len(f["no owner"])
    rows = card.rows(before, after, budget.per_step, budget.trigger,
                     60_000, ("v9", drift.tokens(v9), bad))
    emit("context card, as of May 31, 2026 (lab replay)")
    for r in rows:
        mark = "*" if r.name == card.HIGHLIGHT else " "
        emit(f"{mark} {r.name:<22} {r.value:<26} "
             f"{'ok' if r.ok else 'FAIL'}")
    kinds = Counter(json.loads(ln)["event"] for ln in trail.lines)
    emit(f"trail: {len(trail.lines)} lines "
         f"({', '.join(f'{k} {v}' for k, v in sorted(kinds.items()))})")
    emit(f"trail links: {'ok' if not check_trail(trail.lines) else 'broken'}")
    if trail.lines:
        emit("first line at " + json.loads(trail.lines[0])["at"])
    failed = [r.name for r in rows if not r.ok]
    if failed:
        emit("CHECK FAILED: " + ", ".join(failed))
        return 1
    emit("check passed")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=("unnoticed",))
    ap.add_argument("--compact-at", type=float, default=0.70)
    ap.add_argument("--retrieved-first", action="store_true")
    ap.add_argument("--lengths", action="store_true")
    a = ap.parse_args(argv)
    budget = Budget(BUDGET, compact_at=a.compact_at)
    if a.inject:
        return part_card(a.seed, budget, a.inject)
    parts = [a.part] if a.part else list(PARTS)
    code = 0
    for i, p in enumerate(parts):
        if i:
            emit()
        emit(f"-- {p} --")
        if p == "budget":
            part_budget(a.seed)
        elif p == "opening":
            part_opening()
        elif p == "assemble":
            part_assemble(a.retrieved_first)
        elif p == "compact":
            part_compact(a.seed, budget, a.lengths)
        elif p == "verify":
            part_verify()
        elif p == "isolate":
            part_isolate(a.seed, budget)
        elif p == "drift":
            part_drift()
        elif p == "alarms":
            part_alarms(a.seed, budget)
        elif p == "card":
            code = part_card(a.seed, budget)
    return code


if __name__ == "__main__":
    sys.exit(main())
