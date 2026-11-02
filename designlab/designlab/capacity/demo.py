"""Chapter 10 lab: the Capacity Model on 90 days of pilot traces.

    python3 -m capacity.demo                    # everything, seed 10
    python3 -m capacity.demo --part budget      # one part
    python3 -m capacity.demo --inject per-call  # the p95 that lied
    python3 -m capacity.demo --retry-scale 2    # Try It: double retries
    python3 -m capacity.demo --util 0.95        # Try It: limit at 95%
    python3 -m capacity.demo --prefetch         # Try It: fare rules early
    python3 -m capacity.demo --session S018387  # one task, step by step

Offline. No model is called; the traces are the input.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace

from common.text import emit
from corpus.traces import digest, generate_traces

from . import budget as B
from .estimate import estimate, fit_traces
from .queue import kingman, little, minutes_over
from .surge import load_replay, size_surge, storm_check

PARTS = ("traces", "estimate", "queue", "budget", "surge", "predict")
TOLERANCE = 0.10        # prediction must land within 10% of replay


def part_traces(S, f) -> None:
    emit(f"traces-v1 digest {digest(S)}")
    emit(f"  {f.days} days, December 1, 2025, to February 28, 2026")
    emit(f"  sessions {f.sessions:,}; tasks {f.tasks:,}; "
         f"follow-ups {f.sessions - f.tasks:,}")
    emit(f"  mean {f.mean_per_hour:.1f} sessions an hour; Monday "
         f"8 to 10 a.m. runs {f.surge_ratio:.1f}x")


def part_estimate(f, retry_scale: float) -> None:
    emit("capacity = tokens x steps x retries")
    emit(f"  steps per task: median {f.steps_median:.1f}, p95 "
         f"{f.steps_p95:.1f} (fit), {f.steps_p95_seen:.0f} (seen), "
         f"mean {f.steps_mean:.2f}")
    tries = 1 + (f.tries_per_step - 1) * retry_scale
    asks = 1 + (f.asks_per_step - 1) * retry_scale
    emit(f"  model calls run per step {tries:.3f}; "
         f"requests sent {asks:.3f}")
    emit(f"  input tokens per call {f.tokens_in:,.0f}; "
         f"output {f.tokens_out:,.0f}")
    e = estimate(f, f.mean_per_hour, retry_scale)
    emit(f"  input tokens per task {e.tokens_per_task:,.0f}")
    emit(f"  tool calls per task {f.tools_per_task:.2f}; "
         f"follow-up calls {f.follow_calls:.2f}")
    emit(f"  {'at the ceiling':<26}{'mean hour':>12}{'Monday surge':>15}")
    e = estimate(f, 4_340_000 / 8760, retry_scale)
    s = estimate(f, 4_340_000 / 8760 * f.surge_ratio, retry_scale)
    rows = (("sessions an hour", e.sessions_per_s * 3600,
             s.sessions_per_s * 3600, ",.0f"),
            ("model calls a second", e.model_calls_per_s,
             s.model_calls_per_s, ".2f"),
            ("tool calls a second", e.tool_calls_per_s,
             s.tool_calls_per_s, ".2f"),
            ("input tokens a minute", e.tokens_in_per_min,
             s.tokens_in_per_min, ",.0f"),
            ("sessions open (Little)", e.sessions_in_flight,
             s.sessions_in_flight, ".1f"),
            ("model calls in flight", e.calls_in_flight,
             s.calls_in_flight, ".2f"))
    for name, a, b, fmt in rows:
        emit(f"  {name:<26}{a:>12{fmt}}{b:>15{fmt}}")


def part_queue(S, f) -> None:
    a, o = B.replay(S, B.AS_RUN), B.replay(S, B.OWN)
    emit(f"provider view: per-call p95 {f.call_p95_s:.2f} s "
         f"(mean {f.call_mean_s:.2f} s)")
    emit(f"task view:     per-task p95 {a.p95:.1f} s "
         f"(median {a.median:.1f} s)")
    steps = [x for s in S for x in s.steps]
    hit = sum(1 for x in steps if x.rejected_shared)
    emit(f"rate-limit waits: {hit:,} of {len(steps):,} model calls "
         f"({hit / len(steps):.1%})")
    for h in ((0, 7), (8, 9), (10, 17), (18, 23)):
        xs = [x for s in S for x in s.steps
              if h[0] <= int(s.started[11:13]) <= h[1]]
        w = sum(1 for x in xs if x.rejected_shared) / len(xs)
        emit(f"  {h[0]:02d}:00-{h[1]:02d}:59  {w:6.1%} of calls waited")
    emit(f"replay on its own limit: p95 {o.p95:.1f} s "
         f"(median {o.median:.1f} s)")
    emit("Kingman, one server, 1.04 s calls, Poisson in and out:")
    for rho in (0.5, 0.7, 0.8, 0.9, 0.95):
        emit(f"  utilization {rho:4.0%}: mean wait "
             f"{kingman(rho, f.call_mean_s):5.1f} s")


def part_budget(S, d: B.Design) -> B.Replay:
    r = B.replay(S, d)
    emit(f"design: own limit {d.own_limit}, repeat cap {d.repeat_cap}, "
         f"step cap {d.step_cap}")
    if d.prefetch or d.retry_scale != 1.0:
        emit(f"  prefetch {d.prefetch}, retry scale {d.retry_scale}")
    emit(f"  {'plane':<11}{'p95 s':>9}{'budget s':>10}  ok")
    for plane, p95, bud, ok in B.check_budget(r):
        emit(f"  {plane:<11}{p95:>9.3f}{bud:>10.1f}  "
             f"{'yes' if ok else 'NO'}")
    emit(f"  sum of plane budgets {sum(B.PLANE_BUDGET.values()):.1f} s; "
         f"task budget {B.TASK_BUDGET_S:.0f} s")
    emit(f"  task median {r.median:.1f} s; handed off at step cap "
         f"{r.handoffs} ({r.handoff_share:.2%})")
    return r


def part_surge(S, f, util: float | None) -> None:
    p = size_surge(f)
    emit(f"ceiling: {p.mean_per_hour:,.0f} sessions an hour on average")
    emit(f"  Monday surge {p.surge_per_hour:,.0f} an hour; planned "
         f"x1.25 = {p.planned_per_s:.3f} a second")
    emit(f"  Little: L = {p.planned_per_s:.3f} x {f.residence_s:.0f} s "
         f"= {p.sessions_mean:.0f} sessions open")
    emit(f"  size so 1 instant in 10,000 is over: {p.sessions} sessions")
    emit(f"  model calls {p.calls_per_s:.2f}/s, {p.calls_offered:.2f} "
         f"Erlangs: {p.model_slots} slots (Erlang C, 1% wait)")
    emit(f"  input tokens {p.tpm_mean:,.0f}/min; buy "
         f"{p.tpm_limit:,.0f} ({p.limit_util:.0%} used)")
    emit(f"  minutes over the limit: {p.minutes_over_limit:.1e}")
    if util is not None:
        cpm = p.calls_per_s * 60
        lim = p.tpm_mean / util
        over = minutes_over(lim, cpm, f.tokens_in, f.tokens_in_sd)
        emit(f"  at {util:.0%}: limit {lim:,.0f}/min; "
             f"{over:.1%} of minutes over it")
        emit(f"  Kingman wait at {util:.0%}: "
             f"{kingman(util, f.call_mean_s):.1f} s a call, against "
             f"{kingman(p.limit_util, f.call_mean_s):.1f} s")
    lr = load_replay(S, p.planned_per_s, p.sessions, seed=10)
    emit(f"load replay, 2 hours at the planned rate: {lr.arrivals:,} "
         f"arrivals")
    emit(f"  peak open {lr.peak} of {p.sessions}; refused {lr.refused}")
    st = storm_check(f)
    emit(f"storm check (Chapter 5): {st.changes_per_s} changes/s")
    emit(f"  {st.model_per_change:.2f} model + {st.tools_per_change:.2f} "
         f"tool calls a change = {st.requests_per_s:.1f} requests/s")
    emit(f"  input tokens {st.tpm:,.0f}/min; "
         f"{st.calls_in_flight:.1f} model calls in flight")


def part_predict(S, f, mode: str) -> bool:
    actual = B.replay(S, B.AS_RUN).p95
    pred = B.predict(S, f, mode, seed=10)
    err = (pred - actual) / actual
    emit(f"predicted task p95 ({mode} mode): {pred:.1f} s")
    emit(f"replayed task p95 (90 days, as run): {actual:.1f} s")
    emit(f"  error {err:+.1%}; tolerance {TOLERANCE:.0%}")
    emit(f"  prediction against 40 s budget: "
         f"{'pass' if pred <= B.TASK_BUDGET_S else 'fail'}")
    ok = abs(err) <= TOLERANCE
    emit(f"model check: {'pass' if ok else 'FAIL'}")
    return ok


def show_session(S, sid: str) -> None:
    """One task, step by step: model, wait, and tool seconds as run."""
    s = next(x for x in S if x.sid == sid)
    emit(f"{s.sid} {s.kind} {s.started}")
    emit(f"  steps {len(s.steps)}; needed {s.need}")
    emit(f"  {'step':>4}  {'tool':<15}{'model s':>8}{'wait s':>8}"
         f"{'tool s':>8}  repeat")
    for i, x in enumerate(s.steps, 1):
        line = (f"  {i:>4}  {x.tool or '-':<15}{sum(x.model_s):>8.2f}"
                f"{x.wait_shared:>8.2f}{sum(x.tool_s):>8.2f}  "
                f"{'yes' if x.repeat else ''}")
        emit(line.rstrip())
    for name, d in (("as run", B.AS_RUN), ("March design", B.MARCH)):
        planes, h = B.task_planes(s, d)
        emit(f"  {name}: {sum(planes.values()):.1f} s"
             f"{'; handed off' if h else ''}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="capacity.demo")
    ap.add_argument("--seed", type=int, default=10)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=("per-call",))
    ap.add_argument("--retry-scale", type=float, default=1.0)
    ap.add_argument("--util", type=float)
    ap.add_argument("--prefetch", action="store_true")
    ap.add_argument("--design", choices=("march", "own", "as-run"),
                    default="march")
    ap.add_argument("--session")
    a = ap.parse_args(argv)
    S = generate_traces(a.seed)
    if a.session:
        show_session(S, a.session)
        return 0
    f = fit_traces(S)
    base = {"march": B.MARCH, "own": B.OWN, "as-run": B.AS_RUN}
    d = replace(base[a.design], retry_scale=a.retry_scale, prefetch=a.prefetch)
    mode = "call" if a.inject == "per-call" else "task"
    ok = True
    for i, name in enumerate(PARTS, 1):
        if a.part and a.part != name:
            continue
        emit(f"{i}. {name}")
        if name == "traces":
            part_traces(S, f)
        elif name == "estimate":
            part_estimate(f, a.retry_scale)
        elif name == "queue":
            part_queue(S, f)
        elif name == "budget":
            part_budget(S, d)
        elif name == "surge":
            part_surge(S, f, a.util)
        else:
            ok = part_predict(S, f, mode)
        emit()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
