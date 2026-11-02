"""Chapter 15 demo. Offline: every model answer is a recorded call.

    python3 -m portfolio.demo steps
    python3 -m portfolio.demo gate
    python3 -m portfolio.demo budget
    python3 -m portfolio.demo table [--rule gated|frontier|cost-only]
    python3 -m portfolio.demo cascade
    python3 -m portfolio.demo check [--rule ...]
    python3 -m portfolio.demo scorecard

`check` exits 1 when a wrong answer reaches a step's output or a
high-risk step runs below its floor, so run.sh can require that the
cost-only rule fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter

from common.text import emit

from .budget import BudgetRefused, Candidate, cap
from .cases import router_tasks
from .check import run_check
from .pool import POOL, PoolTransport
from .router import RULES, decide
from .steps import load_steps, policy
from .table import build, gates

TR = None


def _tr():
    global TR
    if TR is None:
        TR = PoolTransport()
    return TR


def cmd_steps(_a) -> int:
    emit(f"{'step':<14}{'kind':<9}{'risk':<7}{'floor':<7}candidates")
    for s in load_steps().values():
        cands = " ".join(c.label for c in s.candidates)
        if s.cascade:
            cands += " " + ">".join(s.cascade)
        emit(f"{s.name:<14}{s.kind:<9}{s.risk:<7}{s.floor:<7}{cands}")
    return 0


def cmd_gate(_a) -> int:
    steps = load_steps()
    emit(f"{'step':<14}{'candidate':<15}{'pass':>6}{'p95 s':>7}"
         f"{'$/call':>9}  gate")
    for name, gs in gates(steps, _tr()).items():
        lim = steps[name].contract
        for g in gs:
            emit(f"{name:<14}{g.label:<15}{g.passed:>3}/{g.total:<2}"
                 f"{g.p95_s:>7.1f}{g.mean_usd:>9.5f}  "
                 f"{'pass' if g.ok else 'FAIL'}")
        emit(f"{'':<14}limits: p95 {lim.p95_latency_s:g} s, "
             f"${lim.max_cost_usd:g} a call")
    return 0


def _usage_by_effort(step: str):
    """Output and thinking tokens from the recorded calls of one step,
    by model and reasoning budget."""
    c = load_steps()[step].contract
    rows: dict[tuple, list] = {}
    for f in sorted(POOL.glob("*.json")):
        d = json.loads(f.read_text())
        req, u = d["request"], d["response"]["usage"]
        if req.get("system") != c.system:
            continue
        eff = req.get("output_config", {}).get("effort", "default")
        th = (u.get("output_tokens_details") or {}).get(
            "thinking_tokens", 0)
        rows.setdefault((req["model"], eff), []).append(
            (u["output_tokens"], th))
    return rows


def cmd_budget(_a) -> int:
    pol = policy()
    emit("refund-rule, recorded calls, by model and reasoning budget")
    emit(f"{'model':<19}{'effort':<9}{'calls':>6}{'out tok':>9}"
         f"{'thinking':>10}")
    for (m, eff), xs in sorted(_usage_by_effort("refund-rule").items()):
        out = sum(x[0] for x in xs) / len(xs)
        th = sum(x[1] for x in xs) / len(xs)
        emit(f"{m:<19}{eff:<9}{len(xs):>6}{out:>9.0f}{th:>10.0f}")
    mx = pol["limits"]["max_effort"]
    emit(f"control-plane cap: effort {mx}")
    for lab in ("mid@high", "mid@max"):
        try:
            cap(Candidate.parse(lab), mx)
            emit(f"  {lab:<9} allowed")
        except BudgetRefused as e:
            emit(f"  {lab:<9} refused: {e}"[:70])
    return 0


def cmd_table(a) -> int:
    t = build(load_steps(), _tr(), a.rule)
    emit(f"rule {a.rule}")
    emit(f"{'step':<14}{'route':<16}{'why':<18}evidence")
    for r in t.values():
        emit(f"{r.step:<14}{r.label:<16}{r.reason:<18}{r.evidence}"[:70])
    return 0


def cmd_cascade(_a) -> int:
    steps = load_steps()
    g = next(x for x in gates(steps, _tr())["change-intent"]
             if ">" in x.label)
    emit(f"change-intent cascade {g.label} on {g.total} golden cases")
    emit(f"  escalated {g.escalated}, right {g.passed}/{g.total}, "
         f"${g.mean_usd:.5f} a case")
    for e in g.escalations:
        emit(f"  {e}")
    table = build(steps, _tr(), "gated")
    res = run_check(router_tasks(), steps, table, _tr(), "gated")
    cr = res.cascade_runs()
    why = Counter(w for r in cr for w in r.reasons)
    emit(f"router tasks: {len(cr)} cascade steps, "
         f"{sum(r.escalated for r in cr)} escalated "
         f"({res.escalation_rate:.0%})")
    lim = policy()["limits"]["escalation_alert"]
    emit(f"  alert above {lim:.0%}: "
         f"{'ALERT' if res.escalation_rate > lim else 'quiet'}")
    for w, n in sorted(why.items()):
        emit(f"  {w}: {n}")
    return 0


def _check(rule: str):
    steps = load_steps()
    table = build(steps, _tr(), rule)
    return steps, run_check(router_tasks(), steps, table, _tr(), rule)


def cmd_check(a) -> int:
    steps, r = _check(a.rule)
    person = sum(x.outcome == "person" for x in r.runs)
    hi = r.high_risk_on(steps, "small")
    emit(f"rule {a.rule}: {r.n_tasks} tasks, {len(r.runs)} model steps")
    emit(f"  tasks right {r.success}/{r.n_tasks}, wrong answers "
         f"{sum(x.outcome == 'wrong' for x in r.runs)}, "
         f"to a person {person}")
    emit(f"  cost per task ${r.cost_per_task:.5f}")
    ends = ", ".join(f"{m} {r.share_ending_on(m):.0%}"
                     for m in ("small", "mid", "frontier", "person"))
    emit(f"  steps ending on: {ends}")
    emit(f"  high-risk steps on small: {hi}")
    for x in r.runs:
        if x.outcome != "right":
            emit(f"  {x.task} {x.step} on {x.model}: {x.outcome}")
    bad = hi > 0 or any(x.outcome == "wrong" for x in r.runs)
    if bad:
        emit("CHECK FAILED")
    return 1 if bad else 0


def cmd_scorecard(_a) -> int:
    steps = load_steps()
    gs = gates(steps, _tr())
    tasks = router_tasks()
    # April's all-frontier configuration was not re-run on the tasks:
    # it is priced from the frontier gate runs, step by step.
    front = {n: next(g.mean_usd for g in v if g.label == "frontier")
             for n, v in gs.items()}
    priced = sum(front[s] for t in tasks for s in t["steps"]) / len(tasks)
    emit(f"{'rule':<11}{'right':>7}{'$/task':>10}{'on small':>10}"
         f"{'hi-risk small':>15}")
    emit(f"{'frontier':<11}{'n/a':>7}{priced:>10.5f}{'0%':>10}{0:>15}")
    for rule in ("gated", "cost-only"):
        table = decide(steps, gs, rule,
                       policy()["limits"]["max_effort"],
                       tuple(policy()["verifier"]["required_below_mid"]))
        r = run_check(tasks, steps, table, _tr(), rule)
        emit(f"{rule:<11}{r.success:>4}/{r.n_tasks:<2}"
             f"{r.cost_per_task:>10.5f}"
             f"{r.share_ending_on('small'):>10.0%}"
             f"{r.high_risk_on(steps, 'small'):>15}")
    emit("frontier row: priced from its gate runs, not run on the tasks")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd")
    for n in ("steps", "gate", "budget", "cascade", "scorecard"):
        sub.add_parser(n)
    for n in ("table", "check"):
        p = sub.add_parser(n)
        p.add_argument("--rule", choices=RULES, default="gated")
    a = ap.parse_args(argv)
    fn = globals().get(f"cmd_{a.cmd}")
    if fn is None:
        ap.print_help()
        return 2
    return fn(a)


if __name__ == "__main__":
    sys.exit(main())
