"""Chapter 39 lab: change and release for the servicing agent.

    python3 -m release.demo                       # every part
    python3 -m release.demo --part gate           # one part
    python3 -m release.demo --part gate --alone   # model change alone
    python3 -m release.demo --part whatif --steps 12
    python3 -m release.demo --part canary --task rebooking

Offline: no model call and no key. Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
from collections import Counter

from common.text import emit
from harness import manifest as M

from . import abtest as AB
from . import bundle as B
from . import canary as C
from . import gate as RG
from . import log as L
from . import pipeline as P
from . import rollback as R
from . import shadow as S


def harness_101(steps: int = 16) -> tuple[str, dict]:
    m = M.apply_overrides(M.resolve(M.load("servicing-1.0.0")),
                          {"version": "1.0.1", "budgets.steps": steps})
    return M.short(M.manifest_hash(m)), {"budgets.steps": steps}


NOTICE7 = ("Tell the traveler what changed, what we did, and what "
           "happens next, in that order, in plain words.")


def july23() -> B.Bundle:
    """The active bundle on Thursday, July 23, after R-0713 to R-0722."""
    b = B.base().with_part("tool", "payments", "3.1+b44")
    b = b.with_part("policy", "", "pb-2026.07.13")
    p = dict(b.prompt)
    del p["notice@6"]
    b = B.replace(b, prompt=tuple(sorted(p.items())))
    b = b.with_prompt("notice@7", NOTICE7)
    b = b.with_part("memory", "traveler",
                    "schema@2;retention@2;index@2026-07")
    return b.with_part("harness", "servicing-1.0.1", harness_101()[0])


def r0723() -> B.Bundle:
    return july23().with_part("harness", "servicing-1.1.0",
                              B.harness_hash("servicing-1.1.0"))


def console_edit() -> B.Bundle:
    text = B.PROMPTS["refund-reason@1.3"] + " "
    return B.base().with_prompt("refund-reason@1.3", text)


def part_bundle(a) -> None:
    b = B.base()
    emit("== the bundle running on Monday, July 13, 2026 ==")
    for kind, val in b.parts().items():
        if isinstance(val, dict):
            for k, v in val.items():
                emit(f"  {kind:8} {k:18} {v}")
        else:
            emit(f"  {kind:8} {'':18} {val}")
    emit(f"bundle hash {b.hash}")
    emit()
    j = july23()
    emit(f"July 23, after R-0713 to R-0722: {j.hash}")
    emit(f"  kinds changed since July 13: {', '.join(b.changed(j))}")
    c = r0723()
    emit(f"R-0723 candidate {c.hash}, parent {j.hash}")
    emit(f"  kinds changed: {', '.join(j.changed(c))}")
    for line in j.detail(c):
        emit(f"  {line}")
    emit()
    e = console_edit()
    emit("one space added to refund-reason@1.3 in a console")
    emit(f"  bundle {b.hash} -> {e.hash}")
    for line in b.detail(e):
        emit(f"  {line}")


def part_log(a) -> None:
    emit("== the release log, July 13 to August 31, 2026 ==")
    emit(f"{'release':8}{'kind':8}{'change':31}{'path':>23}")
    short = {"gate": "G", "shadow": "S", "ab": "A", "canary": "C",
             "full": "F"}
    for e in L.LOG:
        path = ">".join(short[p] for p in e.path.split(">"))
        if e.result == "rolled_back":
            path += ">ROLLBACK"
        emit(f"{e.rid:8}{e.kind:8}{e.change:31}{path:>23}")
    c = L.counts()
    emit("G gate, S shadow, A fixed-horizon A/B, C canary, F full")
    emit(f"releases {c['releases']}; the June registry would have "
         f"counted {c['june_rule']}")


def _gate_tasks():
    from evals import golden as G, harvest as H, online as O
    return H.admit(G.build(), H.label(H.clusters(O.production())),
                   "2026-07-06")


def part_gate(a) -> None:
    tasks = _gate_tasks()
    g = RG.BundleGate(tasks=tasks)
    emit(f"== the gate on gs-2026.07 ({len(tasks)} tasks, pass^3) ==")
    rels = [
        RG.Candidate("R-0710", "2026-07-10", "pb-2026.07.13 (early)",
                     "policy"),
        RG.Candidate("R-0713", "2026-07-13", "payments 3.1: split",
                     "tool", splits=True),
        RG.Candidate("R-0723", "2026-07-23", "harness 1.1.0", "harness",
                     manifest="servicing-1.1.0", shape="state_machine",
                     extra_read=0.0, swap_read=0.0, splits=True),
    ]
    if a.alone:
        rels.append(RG.Candidate(
            "R-0731x", "2026-07-31", "new classifier model, alone",
            "model", reason_flip=0.15, splits=True))
    for rel in rels:
        res = g.evaluate(rel)
        emit(g.record(res)[11:])
        emit(f"  cost per task ${res.cost_per_task}")
        for r in res.reasons:
            emit(f"  {r}")
        if res.failing and not res.passed:
            cls = Counter(v[0][1] for v in res.failing.values())
            emit("  failing: " + ", ".join(f"{k} {n}"
                                           for k, n in cls.items()))


def part_whatif(a) -> None:
    b = B.base()
    h, ov = harness_101(a.steps)
    cand = b.with_part("harness", "servicing-1.0.1", h)
    emit(f"== what-if: R-0722, steps 24 to {a.steps}, "
         f"2,000 runs of last week ==")
    w = RG.whatif(b, cand, ov, scope=())
    emit(f"  divergent runs {len(w.divergent)}; "
         f"outside the declared scope {len(w.unexpected)}")
    for cid, idx, note in w.divergent[:3]:
        emit(f"  {cid} span {idx}: {note}")
    emit(f"  verdict: {'HOLD' if w.holds else 'pass'}")
    emit()
    cand = b.with_prompt("refund-reason@1.4",
                         B.PROMPTS["refund-reason@1.3"] + " v1.4")
    emit("== what-if: R-0811, refund-reason@1.4 ==")
    w = RG.whatif(b, cand)
    emit(f"  divergent runs {len(w.divergent)}")
    emit(f"  chat spans marked {w.marked_spans} in {w.marked_runs} runs:")
    emit("  replay served the old prompt's answers; the golden set")
    emit("  decides what the new prompt answers")
    emit()
    emit("== what-if: a policy draft with a $500 refund cap ==")
    w = RG.whatif(b, b, policy="refunds-v4-draft", scope=("policy",))
    emit(f"  divergent runs {len(w.divergent)}, all at the policy "
         f"verdict: {len(w.unexpected) == 0}")


def part_canary(a) -> None:
    t = a.task
    emit(f"== canary: harness 1.1.0 on {t}, 5% then 25% then 50% ==")
    fail = (0.037, 0.007) if t == "refund" else (0.007, 0.007)
    for measure in ("latency", "verified"):
        c = C.run(t, *fail, seed=43, measure=measure)
        emit(f"measured on {measure}:")
        for s in c.stages:
            emit(f"  {s.share:>4.0%} {s.days}d runs {s.runs:>3} "
                 f"unverified {s.bad:>2} p95 {s.p95_ms / 1000:.1f}s "
                 f"vs {s.ctrl_p95_ms / 1000:.1f}s p {s.p:.4f}")
        emit(f"  verdict: {c.verdict}")
    if t != "refund":
        return
    emit()
    n, bad, cn, cbad, p = C.pooled(*fail)
    emit("one 5% canary over all task types for 3 days:")
    emit(f"  candidate {bad}/{n} unverified, control {cbad}/{cn}, "
         f"p {p:.2f}")
    pw = C.power(*fail)
    emit("1,000 simulated refund canaries, 3.7% against 0.7%:")
    emit("  stopped at " + ", ".join(
        f"{k:.0%} {pw.get(k, 0)}" for k in (0.05, 0.25, 0.5))
        + f", missed {pw.get('missed', 0)}")
    pa = C.power(0.007, 0.007)
    emit(f"  same bundle as control: false rollbacks "
         f"{1000 - pa.get('missed', 0)} of 1,000")
    emit(f"chance 5,000 runs show a 1-in-10,000 defect: "
         f"{C.p_detect(1e-4, 5000):.1%}")


def part_rollback(a) -> None:
    b, c = july23(), r0723()
    runs = R.inflight()
    for r in runs:
        r.bundle = c.hash
    out = R.rollback(c, b, runs, "07-30 08:40 CDT")
    emit("== rollback of R-0723, Thursday, July 30, 8:40 a.m. CDT ==")
    emit(out["trail"][0])
    total = 0
    for s in R.STATES:
        k = len(out["plan"][s])
        total += k if s != "done" else 0
        emit(f"  {s:18}{k:>4}  {R.RULE[s]}")
    emit(f"in flight {total}; trail lines written {len(out['trail']) - 1}")


def part_memory(a) -> None:
    ws = R.schema3_writes()
    skipped = sum(R.read_v2(w) is None for w in ws)
    emit("== R-0819: traveler memory schema 3, canary on rebooking ==")
    emit(f"records written by canary runs  {len(ws)}")
    emit(f"read by v2 readers (other task types): skipped {skipped}")
    d = [R.downcast(w) for w in ws]
    ok = sum(x is not None for x in d)
    emit(f"rollback: downcast to v2 {ok}, quarantined {len(ws) - ok}")
    emit("fix: readers that know v3 first, writers of v3 second")


def part_shadow(a) -> None:
    sh = S.run()
    emit("== shadow: classifier on the August snapshot, planned ==")
    emit(f"recorded rebookings, Aug 10 to 23   {sh.runs:,}")
    emit(f"effect calls recorded and refused   {len(sh.tool.calls):,}")
    emit(f"proposals that differ               {sh.n_differ} "
         f"({sh.n_differ / sh.runs:.1%})")
    for k in S.KINDS:
        if k in sh.differ:
            emit(f"  {k:34} {sh.differ[k]:>4}")
    emit(f"reviewed before any exposure        {sh.reviewed}")


def part_ab(a) -> None:
    n = AB.sample_size(0.09, 0.07)
    emit("== A/B: notice@8 against notice@7, notify only ==")
    emit("repeat contact within 48 h: 9.0% now; detect 2.0 points")
    emit(f"alpha 0.05, power 0.80: {n:,} notices per arm, fixed")
    xa, xb, p = AB.fixed(0.09, 0.071, n)
    emit(f"Aug 26 to 30: v7 {xa}/{n} ({xa / n:.1%}), "
         f"v8 {xb}/{n} ({xb / n:.1%}), p {p:.3f}")
    end, peek = AB.peeking()
    emit("A/A, 2,000 tests, 10 days, 600 a day per arm:")
    emit(f"  read once at the end: false alarms {end:.1%}")
    emit(f"  read daily, stop at first p < 0.05: {peek:.1%}")


def part_bandit(a) -> None:
    share, bad = AB.bandit()
    emit("== a bandit rewarded on approval (marketplace, composite) ==")
    emit("arm B approves 88% against 80%; wrong payouts 6% against 1%")
    emit("share of claims sent to B: " + ", ".join(
        f"day {d + 1} {share[d]:.0%}" for d in (0, 2, 6)))
    emit(f"wrong payouts in 30 days: A {bad[0]}, B {bad[1]:,}")
    emit(f"all claims on A would have paid about "
         f"{int(30 * 4000 * 0.01):,} wrongly")


def part_deploy(a) -> None:
    p = P.Pipeline()
    b, c = july23(), r0723()
    rec = B.Record("R-0723", "2026-07-23", c, b.hash, b.changed(c),
                   "Daniel Price")
    p.submit(rec)
    emit("== the deploy step ==")
    tries = [("R-0723 before its gate pass", c, "refund", "canary",
              0.05, "canary"),
             ("R-0723 after its gate pass", c, "refund", "canary",
              0.05, "canary"),
             ("console-edited refund-reason", console_edit(), "refund",
              "full", 1.0, "canary"),
             ("R-0723 under a bandit", c, "refund", "canary", 0.5,
              "bandit")]
    for i, (label, bb, t, st, sh, m) in enumerate(tries):
        if i == 1:
            p.gate_passed(rec, "07-23")
        try:
            line = p.deploy(bb, t, st, sh, "07-27", method=m)
            emit(f"deploy  {label}")
            emit(f"        {line}")
        except P.Refused as e:
            emit(f"REFUSE  {label}")
            emit(f"        {e}")
    emit()
    seen = [B.trail_line("R-8811", b, "full"),
            B.trail_line("R-8812", console_edit(), "full")]
    bad = B.unbundled(seen, {b.hash, c.hash})
    emit("trail check: runs whose bundle is in no release record")
    for o in bad:
        emit(f"  {o['run']} bundle {o['bundle']}: unbundled change")


def part_card(a) -> None:
    for line in L.card():
        emit(line)


PARTS = {"bundle": part_bundle, "log": part_log, "gate": part_gate,
         "whatif": part_whatif, "canary": part_canary,
         "rollback": part_rollback, "memory": part_memory,
         "shadow": part_shadow, "ab": part_ab, "bandit": part_bandit,
         "deploy": part_deploy, "card": part_card}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS))
    ap.add_argument("--alone", action="store_true")
    ap.add_argument("--steps", type=int, default=16)
    ap.add_argument("--task", default="refund", choices=sorted(C.VOLUME))
    a = ap.parse_args()
    for name, fn in PARTS.items():
        if a.part in (None, name):
            fn(a)
            if a.part is None:
                emit()


if __name__ == "__main__":
    main()
