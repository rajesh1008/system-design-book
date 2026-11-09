"""Chapter 35 demo: python -m tracing.demo --part NAME

Parts: spans, gap, cost, complete, inject, replay, version, alerts,
sampling, card. Offline; nothing here calls a model or reads a key.
"""
from __future__ import annotations

import argparse
import json
from decimal import Decimal

from common.text import emit
from harness.manifest import apply_overrides
from harness.world import World, cases

from . import alerts, complete, cost, questions, replay, sampling
from . import conventions as c
from .run import Gateway, fleet, harness, live
from .spans import clock_at, export

CASE = "R-0002"


def _case(cid: str = CASE):
    return next(x for x in cases(1000) if x.cid == cid)


def _one(skip=(), stray=None):
    gw = Gateway()
    r = live(_case(), harness(), World(), gw, 0, skip, stray=stray)
    return r, gw


def _tree(r) -> None:
    depth = {None: -1}
    for s in r.trace:
        d = depth[s.parent_id] + 1
        depth[s.span_id] = d
        usd = s.attrs.get(c.COST)
        tail = f"${Decimal(usd):.4f}" if usd and s.name.startswith(
            "chat ") else ""
        if s.name.startswith("policy "):
            tail = s.attrs.get(c.POLICY_VERDICT, "")
        if s.name.startswith("verify "):
            tail = s.attrs.get(c.VERIFY_RESULT, "")
        if s.attrs.get(c.VERDICT) == "refused":
            tail = "refused"
        emit(f"{'  ' * d + s.name:<44}{s.ms:>7,} ms  {tail}".rstrip())


def part_spans() -> None:
    r, _ = _one()
    root = r.trace[0]
    emit(f"trace {root.trace_id[:12]}  case {r.cid}  "
         f"start {clock_at(root.start_ms)}")
    emit(f"{len(r.trace)} spans, {r.steps} steps, {r.model_calls} "
         f"model calls, outcome {r.outcome}")
    emit()
    _tree(r)
    emit()
    s = next(x for x in r.trace
             if x.attrs.get(c.TOOL_NAME) == "refund_ticket")
    emit(f"attributes on '{s.name}':")
    for k in sorted(s.attrs):
        emit(f"  {k:<28} {s.attrs[k]}")


def _qa(r, gw) -> int:
    trail = [x for x in gw.trail.lines if json.loads(x)["run"] == r.cid]
    n = 0
    for i, (q, a) in enumerate(questions.answers(r.trace, r.evidence,
                                                 trail), 1):
        n += a is not None
        emit(f"  {i:>2}. {q:<22} {a if a is not None else '-- no answer'}")
    return n


def part_gap() -> None:
    for label, skip in (("policy engine instrumented", ()),
                        ("policy engine not instrumented", ("policy",))):
        r, gw = _one(skip)
        emit(f"{label}: {len(r.trace)} spans")
        n = _qa(r, gw)
        emit(f"  answered from the trace: {n} of 11")
        rep = complete.check(r.cid, r.trace, gw.trail.lines)
        emit(f"  completeness: {'PASS' if rep.ok else 'FAIL'}"
             + ("" if rep.ok else f"  {rep.problems[0]}"))
        emit()


def part_cost() -> None:
    r, _ = _one()
    ds = cost.stamp(r.trace, r.evidence)
    emit(f"case {r.cid}: cost on each chat span")
    for s in r.trace:
        if s.name.startswith("chat "):
            a = s.attrs
            emit(f"  {s.name:<26} in {a[c.IN_TOKENS]:>5,} "
                 f"cached {a[c.CACHE_READ]:>5,} out {a[c.OUT_TOKENS]:>3}"
                 f"  ${Decimal(a[c.COST]):.4f}")
    emit(f"  run total ${r.cost:.4f}; decisions: "
         + ", ".join(f"{d['kind']} ${d['usd']:.4f}" for d in ds))
    emit()
    fl = fleet(1000)
    tot = sum(x.cost for x in fl.results)
    emit(f"1,000 runs: model spend ${tot:.2f}, "
         f"${tot / 1000:.4f} per run")
    by = {}
    for x in fl.results:
        for k, v in cost.by_span_kind(x.trace).items():
            by[k] = by.get(k, Decimal(0)) + v
    for k, v in sorted(by.items(), key=lambda kv: -kv[1]):
        emit(f"  {k:<20} ${v:>7.2f}  {v / tot:>5.1%}")
    emit()
    emit(f"{'cost per decision':<18}{'n':>6}{'p50':>10}{'p95':>10}"
         f"{'max':>10}")
    for k, v in sorted(cost.distribution(fl.results).items()):
        emit(f"{k:<18}{v['n']:>6,}{v['p50']:>10.4f}{v['p95']:>10.4f}"
             f"{v['max']:>10.4f}")


def _report(label, fl) -> dict:
    rep = complete.fleet_report(fl)
    emit(f"{label}: {rep['runs']:,} runs")
    emit(f"  steps traced {rep['steps_traced']:,} of {rep['steps']:,} "
         f"({rep['steps_traced'] / rep['steps']:.1%})")
    emit(f"  calls traced {rep['calls_traced']:,} of {rep['calls']:,} "
         f"({rep['calls_traced'] / rep['calls']:.2%})")
    emit(f"  runs failing the check: {len(rep['failed'])}")
    emit(f"  verdict: {'PASS' if not rep['failed'] else 'FAIL'}")
    return rep


def part_complete() -> None:
    _report("normal day", fleet(1000))


def part_inject() -> None:
    rep = _report("one notify fallback with no span", fleet(
        1000, stray_every=250))
    for f in rep["failed"]:
        emit(f"  {f.run}: {f.problems[0]}")
    assert rep["failed"], "the stray call must fail the check"
    emit("injection caught: the trail has calls the trace does not")


def part_replay() -> None:
    r, _ = _one()
    text = export(r.trace, r.evidence)
    rp = replay.replay(_case(), text, harness())
    emit(f"strict replay of {r.cid}: {len(text):,} bytes of trace, "
         f"{len(rp.spans)} spans")
    emit(f"  outcome {rp.outcome}, same as production: {rp.diff.same}")
    emit(f"  digest prod {replay.trace_digest(r.trace)}  "
         f"replay {replay.trace_digest(rp.spans)}")
    emit()
    b = replay.bench(fleet(1000), harness())
    emit(f"strict replay, {b['runs']:,} runs from exported traces:")
    emit(f"  diverged {b['diverged']}; compute p50 {b['p50_ms']:.2f} ms, "
         f"p95 {b['p95_ms']:.2f} ms")
    emit("  (compute only; production adds the trace-store fetch)")


def part_version() -> None:
    fl = fleet(1000)
    h = harness()
    by = {x.cid: x for x in cases(1000)}
    trials = (
        ("budgets.steps 24 -> 8", apply_overrides(
            h, {"budgets.steps": 8}), "refunds-v3"),
        ("budgets.task_usd 1.00 -> 0.05", apply_overrides(
            h, {"budgets.task_usd": "0.05"}), "refunds-v3"),
        ("policy refunds-v4-draft ($500)", h, "refunds-v4-draft"),
    )
    for label, hh, pol in trials:
        n, first = 0, None
        for r in fl.results:
            rp = replay.replay(by[r.cid], export(r.trace, r.evidence),
                               hh, pol)
            if not rp.diff.same:
                n += 1
                first = first or (r.cid, rp.diff)
        emit(f"what-if {label}")
        emit(f"  runs that diverge: {n:,} of 1,000")
        if first:
            cid, d = first
            emit(f"  first: {cid} span {d.index}: production "
                 f"'{d.production}'")
            emit(f"         replay '{d.replay}' ({d.note[:30]})")


def part_alerts() -> None:
    days = (("normal", {}),
            ("A", {"refuse_reads": 0.08}),
            ("B", {"cache": False}),
            ("C", {"reconcile_faults": 6}),
            ("D", {"stray_every": 250}))
    ms = {k: alerts.metrics(fleet(1000, **kw)) for k, kw in days}
    emit("A refused reads 8%  B cache off  C reconcile lag  D stray call")
    emit(f"{'rule':<28}" + "".join(f"{k:>8}" for k, _ in days))
    for group, rules in (("pages", alerts.RULES),
                         ("dashboard only", alerts.NOISE)):
        emit(f"-- {group}")
        for rule in rules:
            row = "".join(f"{'FIRE' if ms[k][rule.metric] > rule.threshold else '-':>8}"
                          for k, _ in days)
            emit(f"{rule.name:<28}{row}")
    emit("-- measured")
    fmt = {"incomplete_runs": "{:.0f}", "unverified_effects": "{:.0f}",
           "refused_read_share": "{:.1%}",
           "cost_per_decision_p95": "${:.3f}",
           "handoff_share": "{:.1%}"}
    for rule in alerts.RULES:
        f = fmt[rule.metric]
        row = "".join(f"{f.format(ms[k][rule.metric]):>8}"
                      for k, _ in days)
        emit(f"{rule.name:<28}{row}")
    emit()
    for rule in alerts.RULES:
        emit(f"{rule.name:<28}{rule.owner:<13}{rule.action[:29]}")


def part_sampling() -> None:
    gb = 1e9
    big = sampling.buffer_bytes(18_000, 1_100, 20, 45)
    emit("worked problem: 18,000 spans/s, 1,100 B, 20 s wait, 45 s stall")
    emit(f"  live {big['live'] / gb:.3f} GB + stall {big['pause'] / gb:.3f}"
         f" GB = {big['total'] / gb:.3f} GB")
    emit(f"  per replica, 3 replicas, N+1, x2.5 objects: "
         f"{sampling.per_replica(big['total'], 3) / gb:.2f} GB")
    small = sampling.buffer_bytes(45, 900, 20, 45)
    emit(f"Lakeshore storm peak: 45 spans/s, 900 B: "
         f"{small['total'] / 1e6:.1f} MB")
    emit()
    fl = fleet(1000)
    kept = {"effect": 0, "error_or_handoff": 0, "random": 0,
            "dropped": 0}
    kept_runs, rnd = [], []
    for r in fl.results:
        eff = any(s.attrs.get(c.TOOL_KIND) == "effect"
                  and s.attrs.get(c.VERDICT) == "allowed"
                  for s in r.trace)
        err = any(s.status == "ERROR" for s in r.trace)
        tid = r.trace[0].trace_id
        k = sampling.decide(r.trace[0].attrs, eff, err, tid)
        kept[k.why] += 1
        if k.keep:
            kept_runs.append(r)
        if sampling.in_random(tid):
            rnd.append(r)
    emit(f"keep policy over 1,000 runs (random stream p = "
         f"{sampling.RANDOM_P}):")
    for k, v in kept.items():
        emit(f"  {k:<18}{v:>5}")
    true = sum(r.outcome == "declined" for r in fl.results) / 1000
    naive = sum(r.outcome == "declined" for r in kept_runs) \
        / len(kept_runs)
    k = sum(r.outcome == "declined" for r in rnd)
    lo, hi = sampling.wilson(k, len(rnd))
    emit(f"decline rate, every run          {true:.1%}")
    emit(f"decline rate, kept traces        {naive:.1%}")
    emit(f"random stream: {k} of {len(rnd)} = {k / len(rnd):.1%}, "
         f"95% interval {lo:.1%} to {hi:.1%}")


def part_card() -> None:
    fl = fleet(1000)
    rep = complete.fleet_report(fl)
    chats = [s for r in fl.results for s in r.trace
             if s.name.startswith(("chat ", "execute_tool "))]
    priced = sum(1 for s in chats if c.COST in s.attrs)
    ds = cost.distribution(fl.results)["all"]
    b = replay.bench(fl, harness())
    emit("Observability card, servicing 1.0.0 (lab, 1,000 runs)")
    emit(f"  steps traced          {rep['steps_traced'] / rep['steps']:.1%}"
         f"   target 100%")
    emit(f"  calls traced          {rep['calls_traced'] / rep['calls']:.1%}"
         f"   target 100%")
    emit(f"  cost on spans         {priced / len(chats):.1%}"
         f"   target 100%")
    emit(f"  cost/decision p95     ${ds['p95']:.4f}   alert at $0.12")
    emit(f"  strict replay         {b['runs'] - b['diverged']:,} of "
         f"{b['runs']:,} identical, p50 {b['p50_ms']:.2f} ms compute")
    by_run = {}
    for line in fl.gateway.trail.lines:
        by_run.setdefault(json.loads(line)["run"], []).append(line)
    refunds = [r for r in fl.results if r.outcome == "refunded"]
    worst = min(sum(a is not None for _, a in questions.answers(
        r.trace, r.evidence, by_run[r.cid])) for r in refunds)
    emit(f"  audit questions       {worst} of 11 on every one of "
         f"{len(refunds)} refunds")
    emit("  conventions           GenAI, Development, read 2026-11-02")


PARTS = {"spans": part_spans, "gap": part_gap, "cost": part_cost,
         "complete": part_complete, "inject": part_inject,
         "replay": part_replay, "version": part_version,
         "alerts": part_alerts, "sampling": part_sampling,
         "card": part_card}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS), required=True)
    PARTS[ap.parse_args().part]()


if __name__ == "__main__":
    main()
