"""Chapter 34 lab: evaluation as a release gate.

    python3 -m evals.demo                 # every part
    python3 -m evals.demo --part gate     # one part
    python3 -m evals.demo --part harvest --month april   # try it

Parts: what, golden, trajectory, judge, passk, online, harvest, gate,
card. Offline and deterministic; the live judge is evals.live.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace

from common.text import emit

from . import agent as A
from . import gate as GT
from . import golden as G
from . import harvest as H
from . import judge as J
from . import online as O
from . import passk as P
from .score import score
from .trajectory import match

R0609, R0617, R0623 = GT.JUNE[3], GT.JUNE[5], GT.JUNE[8]


def part_what() -> None:
    emit("== what the final answer misses: R-0609 on the 640 ==")
    tasks = G.build()
    judge = J.OfflineJudge()
    final = full = 0
    shown = None
    for t in tasks:
        tr = A.run(t, R0609, 0)
        sc = score(t, tr)
        final += sc.final_only
        full += sc.passed
        if sc.final_only and not sc.passed and shown is None:
            shown = (t, tr, sc)
    emit(f"final answer only: {final} of {len(tasks)} pass")
    emit(f"outcome, path, effects, forbidden: {full} of {len(tasks)} pass")
    t, tr, sc = shown
    emit(f"{t.tid} {t.cls}, paid with card {t.card} (expired)")
    emit(f"  outcome {tr.outcome}: matches, judge "
         f"{judge.score(t.tid, tr.message)} of 10 on wording")
    emit(f"  trajectory {sc.trajectory}")
    emit(f"  effect refund {tr.effects[0][1]} to {tr.effects[0][2]}, "
         f"expected {t.effects[0][2]}")
    emit(f"  forbidden {', '.join(sc.forbidden)}")


def part_golden() -> None:
    emit("== the Golden Set, gs-2026.06 ==")
    tasks = G.build()
    for cls, n in G.by_class(tasks).items():
        emit(f"  {cls:20} {n:4}")
    emit(f"  {'total':20} {len(tasks):4}")
    t = next(x for x in tasks if x.cls == "expired_card" and x.card_on_file)
    emit(f"{t.tid} {t.cls} case {t.case.cid}")
    emit(f"  outcome   {t.outcome}")
    emit(f"  tools     {' > '.join(t.tools[:3])} >")
    emit(f"            {' > '.join(t.tools[3:])}")
    emit(f"  effects   " + "; ".join(" ".join(e) for e in t.effects))
    emit(f"  forbidden {', '.join(t.forbidden[:3])},")
    emit(f"            {', '.join(t.forbidden[3:])}")
    emit(f"  card on file {t.card_on_file}; source {t.source}; "
         f"{t.version}")


def part_trajectory() -> None:
    emit("== trajectories: R-0623, 640 tasks x 3 trials ==")
    tasks = G.build()
    kinds, why = Counter(), Counter()
    strict = 0
    for t in tasks:
        for s in range(3):
            tr = A.run(t, R0623, s)
            k, w = match(t.tools, tr.calls)
            kinds[k] += 1
            strict += tr.calls == list(t.tools)
            if k == "tolerated":
                extra = Counter(tr.calls) - Counter(t.tools)
                why["extra " + ",".join(extra) if extra else
                    "reads reordered"] += 1
    n = sum(kinds.values())
    for k in ("exact", "tolerated", "mismatch"):
        emit(f"  {k:10} {kinds[k]:5}  {100 * kinds[k] / n:5.1f}%")
    for w, c in why.most_common():
        emit(f"    {w:30} {c}")
    emit(f"  a strict sequence check would fail {n - strict} runs")
    t = next(x for x in tasks if x.cls == "refund_eligible")
    bad = ["booking_read", "propose", "fare_calc", "refund_ticket",
           "customer_notify"]
    emit("  propose before fare_calc: " + " ".join(match(t.tools, bad)))
    bad = ["booking_read", "fare_calc", "propose", "refund_ticket",
           "refund_ticket", "customer_notify"]
    k, w = match(t.tools, bad)
    emit(f"  refund twice: {k}, {w.split()[0]}")
    emit(f"    {w.split()[1]}")


def part_judge() -> None:
    emit("== the wording judge, calibrated against the desk ==")
    judge = J.OfflineJudge()
    cal = GT.calibration(judge)
    emit(f"held-out messages {cal.n}, labeled by {cal.label_source}")
    emit(f"agreement {cal.agreement:.1%}, kappa {cal.kappa:.2f} "
         f"(bar {J.KAPPA_MIN:.2f}), pin {cal.pin}")
    items = GT.held_out()
    conf = Counter((judge.passes(k, m), w) for k, m, w, _ in items)
    emit(f"  judge pass, people fail {conf[(True, False)]}; "
         f"judge fail, people pass {conf[(False, True)]}")
    over = [(k, m) for k, m, w, _ in items if m.get("overpromise")]
    emit(f"  overpromises passed {sum(judge.passes(k, m) for k, m in over)}"
         f" of {len(over)}")
    wrong = [(k, m) for k, m, _, ok in items if not ok]
    emit(f"  messages on a wrong effect: {len(wrong)}, judge passed "
         f"{sum(judge.passes(k, m) for k, m in wrong)}")
    try:
        GT.calibration(judge, labels=judge.id)
    except J.NotCalibrated as e:
        emit(f"self-labels: refused ({e})")
    new = J.OfflineJudge(pin="small@2026-06-30")
    emit(f"pin moves to {new.pin}: valid {cal.valid_for(new)}")
    g = GT.Gate(judge=new, cal=cal)
    r = g.evaluate(GT.JUNE[8])
    emit(f"  gate on R-0623: {'pass' if r.passed else 'BLOCKED'}, "
         f"{r.reasons[0]}")
    cal2 = GT.calibration(new)
    emit(f"  recalibrated: kappa {cal2.kappa:.2f}, valid "
         f"{cal2.valid_for(new)}")


def part_passk(n: int = 8) -> None:
    emit(f"== pass@k and pass^k: R-0617, {n} trials per task ==")
    tasks = G.build()
    counts, fails = [], Counter()
    for t in tasks:
        c = 0
        for s in range(n):
            sc = score(t, A.run(t, R0617, s))
            c += sc.passed
            if not sc.passed:
                fails[t.cls] += 1
        counts.append(c)
    emit(f"tasks with a failure {sum(c < n for c in counts)} of "
         f"{len(tasks)}; failed runs {n * len(tasks) - sum(counts)}")
    emit("  " + ", ".join(f"{k} {v}" for k, v in fails.most_common()))
    emit("   k   pass@k   pass^k")
    for k, at, hat in P.table(counts, n):
        if k in (1, 2, 3, 5, 8):
            emit(f"  {k:2}   {at:.4f}   {hat:.4f}")
    emit("per-task, three runs: a task at 7 of 8")
    emit(f"  pass@3 {P.pass_at_k(8, 7, 3):.3f}  "
         f"pass^3 {P.pass_hat_k(8, 7, 3):.3f}")


def part_online() -> None:
    emit("== online: June production refunds (synthetic) ==")
    ps = O.production()
    b = O.board(ps)
    emit(f"traces {b.traces}, all scored without labels")
    emit(f"  ledger agrees with message   {b.verified}")
    emit(f"  forbidden effects            {b.forbidden}")
    emit(f"  trajectory anomalies         {b.anomalies}")
    emit(f"  judge wording pass           {b.wording:.1f}%")
    emit("signals of disagreement")
    for s, c in b.disagreements.most_common():
        emit(f"  {s:32} {c:4}")
    emit("weekly labeled sample (people on the desk)")
    for wk, n, pct in b.weekly:
        emit(f"  week of {wk}  {n} labeled  wording {pct:.1f}%")


def part_harvest(month: str = "june") -> None:
    if month == "april":
        emit("== try it: the March set against April traces ==")
        rel = A.Release("R-0414", "2026-04-14", "batch refunds live",
                        "tool server", reads_ledger=False)
        mix = [m for m in O.MIX if m[0] not in ("split_payment",
                                                 "two_timeouts")]
        ps = O.production(n=3000, seed=414, month=4, mix=mix, release=rel)
        march = G.build(G.MARCH, version="gs-2026.03")
        g = GT.Gate(tasks=march)
        r = g.evaluate(rel)
        emit(f"gate on {rel.rid} with gs-2026.03 ({len(march)} tasks): "
             f"{'pass' if r.passed else 'BLOCKED'}")
        cs = H.clusters(ps)
        for c in cs:
            emit(f"  {len(c.traces):4} {c.signal}, {c.cls}: {c.verdict}")
        emit(f"classes the set lacked: {', '.join(H.missing_classes(march, cs))}")
        return
    emit("== the improvement loop: June disagreements ==")
    ps = O.production()
    cs = H.clusters(ps)
    for c in cs:
        emit(f"{len(c.traces):4} {c.signal}")
        emit(f"     {c.cls}: {c.verdict}")
    cands = H.label(cs)
    emit(f"candidates {len(cands)}, labeled by {H.OWNER}")
    for c in cands[:2] + cands[-1:]:
        emit(f"  {c.task.tid:12} {c.task.cls:23} {c.run.split()[0]}")
    gs = G.build()
    try:
        H.admit(gs, cands, "2026-06-29")
    except H.FrozenBetweenCuts as e:
        emit("admit on 2026-06-29: refused,")
        emit(f"  {e}")
    new = H.admit(gs, cands, "2026-07-06")
    emit(f"admit at the 2026-07-06 cut: {new[-1].version}, "
         f"{len(new)} tasks")


def part_gate() -> None:
    emit("== the Release Gate: June 2026, pass^3 on 640 tasks ==")
    g, rs = GT.run_june()
    for r in rs:
        emit(f"{r.rel.date} {r.rel.rid} {r.rel.kind:11} "
             f"{'pass' if r.passed else 'BLOCKED'}")
        for why in r.reasons:
            emit(f"    {why}")
    emit(f"blocked {sum(not r.passed for r in rs)} of {len(rs)}")
    r = rs[3]
    try:
        g.override(r, "Daniel Price", "fallback is customer-friendly",
                   "refunds to a second card")
    except PermissionError as e:
        emit("override by Daniel Price: refused,")
        emit(f"  {e}")
    try:
        g.override(r, "Sarah Whitfield", "", "")
    except ValueError as e:
        emit("override with no reason: refused,")
        emit(f"  {e}")
    emit()
    emit("== rehearsal: harness 1.1.0 in the sandbox, 2026-06-26 ==")
    rh = g.evaluate(GT.REHEARSAL)
    emit(f"{rh.rel.rid} {'pass' if rh.passed else 'BLOCKED'}: pass^3 "
         f"{rh.passk:.3f}, exact {rh.exact_pct:.1f}%, forbidden "
         f"{sum(rh.forbidden.values())}")
    emit(f"  cost per task ${rh.cost_per_task} against "
         f"${g.last.cost_per_task}")
    line = GT.registry_line(rh, g)
    emit("proposed for the July cut, not written:")
    head, _, tail = line.partition(" gate = ")
    emit("  " + head)
    emit("    gate = " + tail)


def part_card() -> None:
    emit("== Evaluation card, Monday, June 29, 2026 ==")
    g, rs = GT.run_june()
    last = rs[-1]
    cal = g.cal
    b = O.board(O.production())
    cands = H.label(H.clusters(O.production()))
    rows = [("golden tasks", f"{len(g.tasks)} (gs-2026.06)"),
            ("trajectory exact", f"{last.exact_pct:.0f}% ({last.rel.rid})"),
            ("judge kappa", f"{cal.kappa:.2f} on {cal.n}, pin valid"),
            ("releases blocked", f"{sum(not r.passed for r in rs)} of "
             f"{len(rs)}"),
            ("overrides", "0"),
            ("forbidden effects, prod", f"{b.forbidden}"),
            ("candidates waiting", f"{len(cands)} for the July 6 cut")]
    for k, v in rows:
        emit(f"  {k:26} {v}")


PARTS = {"what": part_what, "golden": part_golden,
         "trajectory": part_trajectory, "judge": part_judge,
         "passk": part_passk, "online": part_online,
         "harvest": part_harvest, "gate": part_gate, "card": part_card}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--part", choices=sorted(PARTS))
    p.add_argument("--month", choices=("june", "april"), default="june")
    a = p.parse_args(argv)
    names = [a.part] if a.part else list(PARTS)
    for i, n in enumerate(names):
        if i:
            emit()
        if n == "harvest":
            part_harvest(a.month)
        else:
            PARTS[n]()


if __name__ == "__main__":
    main()
