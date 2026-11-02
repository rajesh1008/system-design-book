"""Chapter 4 lab: the baseline from operations data.

    python3 -m baseline.demo                    # the whole baseline
    python3 -m baseline.demo --inject vendor    # the failing metric
    python3 -m baseline.demo --person-cost 1.1  # Try It Yourself
    python3 -m baseline.demo --count-abandons
    python3 -m baseline.demo --by-carrier
"""
from __future__ import annotations

import argparse

from common.text import emit
from corpus.ops import (AS_OF, OPS_VERSION, PILOT_INCIDENTS, WEIGHTS,
                        generate_ops, ops_digest)
from .autonomy import HONEST, VENDOR, Definition, automation_rate, \
    metric_test
from .cost import decompose
from .errors import dot_clock, refund_error
from .scoreboard import baseline_row
from .volume import count_changes, naive_count

SEED = 2026


def m(x: float) -> str:
    return f"{x / 1e6:,.2f}M"


def volume(t: dict) -> None:
    emit("1. Volume: contacts are not changes")
    bad = naive_count(t)
    emit(f"  naive units of work      {m(bad['units']):>9}  (all contacts)")
    v = count_changes(t)
    emit(f"  contacts                 {m(v['contacts']):>9}")
    emit(f"  contacts about a change  {m(v['contacts_about_a_change']):>9}")
    emit(f"  of which follow-ups      {m(v['follow_ups']):>9}")
    emit(f"  distinct changes         {m(v['changes']):>9}"
         f"  ({v['changes'] / v['contacts']:.1%} of contacts)")
    emit(f"  handled by a person      {v['person_share']:>9.1%}")
    emit("  change type              changes  person")
    for k, n in sorted(v["by_type"].items(), key=lambda kv: -kv[1]):
        emit(f"    {k:22} {n / 1e3:>6,.0f}k  "
             f"{v['person_share_by_type'][k]:>5.0%}")


def cost(t: dict, scale: float) -> None:
    emit("2. Cost per change, by path")
    c = decompose(t, person_scale=scale)
    for path in ("person", "self-service"):
        emit(f"  {path} ({c['share'][path]:.0%} of changes)")
        for pool, usd in c["pools"][path].items():
            emit(f"    {pool:28} ${usd:>6.2f}")
        emit(f"    {'total':28} ${c['per_change'][path]:>6.2f}")
    emit(f"  blended  {c['share']['person']:.2f} x "
         f"{c['per_change']['person']:.2f} + "
         f"{c['share']['self-service']:.2f} x "
         f"{c['per_change']['self-service']:.2f} = "
         f"${c['blended']:.2f}")
    emit(f"  annual handling cost     ${c['annual_usd']:,.0f}")
    emit(f"  check: log minutes {c['log_minutes']:.1f} at $42.00/h = "
         f"${c['log_labor_per_change']:.2f} labor")


def errors(t: dict, by_carrier: bool) -> None:
    emit(f"3. Refund error, as of {AS_OF:%b %d, %Y}")
    e = refund_error(t)
    emit(f"  refunds issued           {m(e['refunds']):>9}")
    emit(f"  naive: found / all       {e['naive_rate']:>9.2%}"
         f"  ({e['found']:,} found)")
    emit(f"  matured cohorts (to {e['cutoff']}) "
         f"{e['matured_rate']:.2%}")
    emit("  month    refunds  found  eventual")
    for mo, (n, f, ev) in e["by_month"].items():
        w = WEIGHTS["ops_refunds"]
        emit(f"  {mo}  {n * w:>8,}  {f * w:>5,}  {ev * w:>8,}")
    emit("  matured rate by carrier refund method")
    for k, r in sorted(e["by_api"].items(), key=lambda kv: -kv[1]):
        emit(f"    {k:12} {r:.2%}")
    d = dot_clock(t)
    emit("  involuntary refunds within 7 business days")
    for path, (share, late) in d.items():
        emit(f"    {path:12} {share:.1%}  ({late:,} late)")
    if by_carrier:
        emit("  matured rate by carrier (worst five, 1,000+ refunds)")
        rows = [(k, r, n) for k, (r, n) in e["by_carrier"].items()
                if n >= 1000 and k != "hotel"]
        for k, r, n in sorted(rows, key=lambda x: -x[1])[:5]:
            emit(f"    {k}  {r:.2%} of {n:,}")


def pilot(t: dict, inject: str | None, abandons: bool) -> int:
    s = t["ops_pilot_sessions"]
    n = len(s) * WEIGHTS["ops_pilot_sessions"]
    emit(f"4. Chatbot pilot, Jul to Sep 2024 ({n:,} sessions)")
    for d in (VENDOR, HONEST):
        emit(f"  {d.name:34} {automation_rate(s, d):>5.0%}")
    if abandons:
        d = Definition("abandons counted as contained",
                       count_handoffs=True, count_unverified=True,
                       count_abandons=True)
        emit(f"  {d.name:34} {automation_rate(s, d):>5.0%}")
    emit("  incidents")
    for i in PILOT_INCIDENTS:
        emit(f"    {i['incident_id']} {i['date']}  {i['chain_gap']}")
    defn = VENDOR if inject == "vendor" else HONEST
    emit(f"  metric test on '{defn.name}'")
    problems = metric_test(s, defn)
    w = WEIGHTS["ops_pilot_sessions"]
    for rule, k in problems.items():
        emit(f"    FAIL {rule}: {k * w:,}")
    if not problems:
        emit("    PASS no hand-offs, abandons or unverified counted")
    return 1 if problems else 0


def board(t: dict) -> None:
    emit("5. Scoreboard at baseline")
    for k, v, who in baseline_row(t):
        emit(f"  {k:26} {v:>12}  {who}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inject", choices=["vendor"])
    ap.add_argument("--person-cost", type=float, default=1.0)
    ap.add_argument("--count-abandons", action="store_true")
    ap.add_argument("--by-carrier", action="store_true")
    a = ap.parse_args(argv)
    t = generate_ops(SEED)
    emit(f"Lakeshore baseline, corpus {OPS_VERSION}, seed {SEED}")
    emit(f"digest {ops_digest(t)[:32]}")
    volume(t)
    cost(t, a.person_cost)
    errors(t, a.by_carrier)
    failed = pilot(t, a.inject, a.count_abandons)
    board(t)
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
