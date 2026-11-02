"""Chapter 17 lab: distilling the classification step.

    python3 -m adapt.demo                     # everything, seed 17
    python3 -m adapt.demo --part tree         # one part
    python3 -m adapt.demo --inject random     # the leaky split
    python3 -m adapt.demo --test-month 2026-04  # Try It: another month
    python3 -m adapt.demo --half              # Try It: half the data
    python3 -m adapt.demo --new-type          # Try It: a 13th type

The teacher part replays the recorded frontier and small-model labels
from adapt/fixtures; `python3 -m adapt.live` records them. No other part
calls a model.
"""
from __future__ import annotations

import argparse
import sys

from common.spend import SpendMeter
from common.text import emit

from . import cost as C
from . import evaluate as E
from . import lab as L
from . import prefs as P
from . import reward as R
from . import teacher as T
from .data import generate
from .tree import MARCUS, walk

PARTS = ("tree", "teacher", "distill", "cost", "prefs", "reward")


def part_tree() -> None:
    emit("adapt.tree: Marcus Bell's request, April 2026, six asks")
    n = 0
    for r in MARCUS:
        v = walk(r)
        n += v.outcome.startswith("adapt")
        emit(f"  {r.ask:<37} node {v.node}  {v.outcome}")
    emit(f"  {n} of {len(MARCUS)} asks reach adaptation")


def part_teacher(seed: int) -> None:
    msgs = generate(seed)
    sim = T.sim_teacher(msgs, seed)
    for month in (None, "2026-05"):
        sample = T.live_sample(msgs, 100, seed, month)
        where = "training months" if month is None else month
        emit(f"teacher labels, recorded: 100 messages, {where}")
        for role in ("frontier", "small"):
            meter = SpendMeter(cap_usd=0.50)
            try:
                got, st = T.label(sample, role, meter, offline=True)
            except LookupError:
                emit(f"  {role}: no fixtures; run python3 -m adapt.live")
                continue
            right = sum(got[m.msg_id] == m.label for m in sample)
            cut = sum(got[m.msg_id] == "unparsed" for m in sample)
            emit(f"  {role:<8} {st['model']:<16} agrees {right}/100; "
                 f"cut off {cut}")
        right = sum(sim[m.msg_id] == m.label for m in sample)
        emit(f"  sim teacher on the same 100: agrees {right}/100")


def part_distill(seed: int, half: bool, new_type: bool,
                 test_month: str, tuned: bool) -> Run:
    r = L.run(seed, half=half, new_type=new_type, test=test_month,
              tau=None if tuned else L.FLOOR)
    emit(f"distill: train {', '.join(L.TRAIN)}")
    cases = len({m.case_id for m in r.train})
    emit(f"  {len(r.train):,} messages, {cases:,} cases, teacher labels")
    emit("  student: TF-IDF + logistic regression")
    o = E.overlap(r.train, r.test)
    why = E.gate(o)
    emit(f"  overlap with {test_month}: cases {o.same_case}, "
         f"text {o.same_text} of {o.test:,}: "
         f"{'FAIL' if why else 'pass'}")
    va = E.score(L.cascade(r.student, r.val, r.teacher, r.tau)[0], r.val)
    emit(f"  validation {L.VAL}: cascade {va.acc:.1%} at tau {r.tau}")
    a = E.score(r.stu, r.test)
    c = E.score(r.cas, r.test)
    f = E.score(r.fr, r.test)
    emit(f"  held-out {test_month}, {len(r.test):,} golden cases:")
    emit(f"    student alone      {a.acc:6.1%}  weakest "
         f"{a.weakest()[0]} {a.weakest()[1]:.0%}")
    emit(f"    student + escalate {c.acc:6.1%}  escalated "
         f"{r.escalated:.1%}")
    emit(f"    frontier teacher   {f.acc:6.1%}")
    oa, ob = E.paired(r.cas, r.fr, r.test)
    emit(f"    paired: only student right {oa}; only frontier {ob}")
    ok, why_p = E.parity(c, f)
    emit(f"  parity: {'PASS' if ok else 'FAIL'} ({why_p})")
    return r


def part_cost(escalated: float) -> None:
    emit("cost per classification step (prices from models.toml)")
    f = C.frontier_step()
    emit(f"  frontier, {C.STEP_IN:,} in / {C.STEP_OUT} out tokens: "
         f"${f:.5f}")
    sm = C.frontier_step("small")
    emit(f"  small model, same prompt:          ${sm:.5f} "
         f"({f / sm:.0f}x less)")
    for name, steps in (("June volume", C.GA_STEPS),
                        ("May pilot", C.PILOT_STEPS)):
        s = C.distilled(escalated, steps)
        emit(f"  {name}, {steps:,} steps a month:")
        emit(f"    serve ${s.serve:.5f} + escalate ${s.escalate:.5f}"
             f" + upkeep ${s.upkeep:.5f}")
        emit(f"    = ${s.student:.5f} a step; frontier / student "
             f"{s.ratio:.1f}x")


def part_prefs(seed: int) -> None:
    cs = P.cards(seed)
    pairs, dropped = P.export(cs)
    emit(f"prefs: {len(cs):,} refund cards, December 2025 to May 2026")
    emit(f"  pairs (wording-only edits)   {len(pairs):,}")
    for k, v in sorted(dropped.items()):
        emit(f"  dropped, {k:<20} {v:,}")
    tr = [p for p in pairs if p.month < "2026-05"]
    te = [p for p in pairs if p.month == "2026-05"]
    code = {c.card_id: c.code for c in cs}
    fixed = sum(P.rule_fix(p.rejected, code[p.card_id]) == p.chosen
                for p in te)
    emit(f"  held-out 2026-05: {len(te)} pairs")
    emit(f"    rule (narrative to house format) removes {fixed} "
         f"({fixed / len(te):.0%})")
    rest = [p for p in te
            if P.rule_fix(p.rejected, code[p.card_id]) != p.chosen]
    rk = P.Ranker.train(tr)
    emit(f"    ranker on all pairs: {sum(map(rk.prefers, te))}/"
         f"{len(te)} prefer the chosen text")
    emit(f"    ranker on the {len(rest)} the rule leaves: "
         f"{sum(map(rk.prefers, rest))}/{len(rest)}")
    emit("  defective drafts approved unedited, by queue depth:")
    for name, n, share in P.wave_through(cs):
        emit(f"    {name:<11} {n:>5,} drafts  {share:5.1%} waved through")


def part_reward(seed: int) -> None:
    emit("reward: 3,000 episodes each; policy at the end")
    for g in (R.naive, R.exists, R.harness):
        pol, ok = R.train(g, seed=seed)
        top = max(pol, key=pol.get)
        emit(f"  {g.__name__:<8} learns {top:<7} ({pol[top]:.0%}); "
             f"verified success {ok:.0%}")


def part_inject(seed: int) -> int:
    tr, te, sc, o = L.leaky(seed)
    emit("inject: a random 80/20 split of the training months")
    emit(f"  test accuracy {sc.acc:.1%} on {sc.n:,} messages")
    why = E.gate(o)
    for w in why:
        emit(f"  overlap: {w}")
    emit("  FAIL: evaluated on the training distribution" if why
         else "  pass")
    return 1 if why else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=("random",))
    ap.add_argument("--test-month", default=L.TEST)
    ap.add_argument("--half", action="store_true")
    ap.add_argument("--new-type", action="store_true")
    ap.add_argument("--tuned", action="store_true",
                    help="tune the threshold on the validation month")
    a = ap.parse_args(argv)
    if a.inject:
        return part_inject(a.seed)
    parts = (a.part,) if a.part else PARTS
    esc = 0.0
    for i, p in enumerate(parts):
        if i:
            emit()
        if p == "tree":
            part_tree()
        elif p == "teacher":
            part_teacher(a.seed)
        elif p == "distill":
            esc = part_distill(a.seed, a.half, a.new_type,
                               a.test_month, a.tuned).escalated
        elif p == "cost":
            if not esc:
                esc = L.run(a.seed).escalated
            part_cost(esc)
        elif p == "prefs":
            part_prefs(a.seed)
        elif p == "reward":
            part_reward(a.seed)
    return 0


Run = L.Run

if __name__ == "__main__":
    sys.exit(main())
