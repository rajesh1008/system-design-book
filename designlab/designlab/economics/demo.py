"""Chapter 38 demo: the bill, the outcome, the policy, the card.

    python3 -m economics.demo                       # every part
    python3 -m economics.demo --part invoice        # June and July
    python3 -m economics.demo --part close [--rule identity]
    python3 -m economics.demo --part kinds [--month August]
    python3 -m economics.demo --part weekly         # tokens, outcomes
    python3 -m economics.demo --part bound          # before the run
    python3 -m economics.demo --part storm          # four regimes
    python3 -m economics.demo --part policy [--envelope 200]
    python3 -m economics.demo --part chargeback [--rule pool]
    python3 -m economics.demo --part chargeback --by use-case
    python3 -m economics.demo --part august
    python3 -m economics.demo --part card

Offline, seeded, Chicago clock (CDT). No model call and no key.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
from dataclasses import replace

from common.text import emit

from . import bill, bound, card, chargeback, outcome, replay
from .policy import DR38, JULY, JULY_COUNTING


def part_invoice(a) -> None:
    emit("== provider invoice by identity ==")
    emit(f"{'identity':<32}{'June':>12}{'July':>12}")
    june = {x.identity: x.usd for x in bill.invoice("June")}
    for x in bill.invoice("July"):
        j = june.get(x.identity)
        js = f"{j:>12,.2f}" if j is not None else f"{'-':>12}"
        emit(f"{x.identity:<32}{js}{x.usd:>12,.2f}")
    jt, yt = bill.total("June"), bill.total("July")
    emit(f"{'total':<32}{jt:>12,.2f}{yt:>12,.2f}")
    emit(f"July / June {yt / jt:.2f}x")
    emit(f"storm calls billed {bill.weekend().billed():,}; "
         f"each ${bill.storm_call().usd('small'):.5f}")
    emit(f"  1,800 in, {bill.STORM_MAX_TOKENS:,} out (max_tokens), "
         f"small model")
    emit(f"INC-6 spend line (input only)  ${bill.estimate_usd():,.2f}")
    emit(f"enforcer counted               $0.00")


def part_close(a) -> None:
    c = outcome.close("July", a.rule)
    lo, mid, hi = outcome.BAND["July"]
    emit(f"== July close, rule: {a.rule} ==")
    emit(f"verified outcomes (agent path)  {c.verified:>10,}")
    emit(f"drivers, Ch18's seven lines     {c.drivers:>10.4f}")
    label = ("storm, pooled 46.7% to agent" if a.rule == "pool"
             else "storm, charged to its owner")
    emit(f"{label:<32}{c.pooled:>10.4f}")
    emit(f"INC-5 rework, 44 rebookings     {c.rework:>10.4f}")
    emit(f"cost per verified outcome       {c.total:>10.4f}")
    emit(f"band ${lo:.2f} / ${mid:.2f} / ${hi:.2f}: "
         f"{'inside' if c.total <= hi else 'above'}")
    d = outcome.drivers("July")
    emit("drivers by line:")
    for k, v in d["lines"].items():
        emit(f"  {k:<20}{v:>11,.2f}{v / d['verified']:>9.4f}")
    emit(f"INC-5 rework ${outcome.inc5_rework():,.2f}: 44 x 24 min "
         f"desk, 40 x $12 credit, 44 x $0.40")
    aug = outcome.close("August")
    emit(f"August, as run: {aug.verified:,} verified, "
         f"${aug.total:.4f}")


def part_kinds(a) -> None:
    emit(f"== cost per verified outcome by kind, {a.month} ==")
    k = outcome.kinds(a.month, a.rule)
    d = outcome.kinds(a.month, "identity")
    emit(f"{'kind':<10}{'as closed':>16}{'own spend only':>16}")
    for name in k:
        emit(f"{name:<10}{k[name]:>16.3f}{d[name]:>16.3f}")
    c = outcome.close(a.month, a.rule)
    emit(f"{'all':<10}{c.total:>16.3f}")


def part_weekly(a) -> None:
    emit("== the weekly report, two ways ==")
    emit(f"{'week':<16}{'$ per Mtok':>12}{'$ per verified':>16}")
    rows = outcome.weekly()
    for name, tok, per in rows:
        emit(f"{name:<16}{tok:>12.3f}{per:>16.3f}")
    t0, t1 = rows[2][1], rows[3][1]
    p0, p1 = rows[2][2], rows[3][2]
    emit(f"storm week: tokens {t1 / t0 - 1:+.0%}, "
         f"outcomes {p1 / p0 - 1:+.0%}")


def part_bound(a) -> None:
    emit("== waiver watch: the worst case before the first call ==")
    for c in (bound.JULY, bound.AUGUST):
        emit(f"{c.name}: attempts {c.attempts}, re-queues "
             f"{'no cap' if c.requeues is None else c.requeues}")
        for s in c.steps:
            emit(f"  {s.name:<8}{s.role:<6}{s.tokens_in:>7,} in "
                 f"{s.max_tokens:>7,} max  ${s.worst():.5f}")
        t = bound.per_trigger(c)
        emit(f"  per run ${bound.per_run(c):.4f}; per notice "
             f"{'unbounded' if t is None else f'${t:.4f}'}")
    emit(f"run budget $0.25; July's run worst case is over it")


def _row(r) -> str:
    return (f"{r.policy:<24}{r.billed:>11,.2f}{r.counted:>11,.2f}"
            f"{r.servicing_429_min:>8}")


def part_storm(a) -> None:
    emit("== July 25-26 replayed: what the provider bills ==")
    emit(f"{'policy':<24}{'billed':>11}{'counted':>11}{'429 min':>8}")
    emit(_row(replay.run(JULY)))
    usd, over = replay.rate_share_only()
    emit(f"{'rate share 20%, no cap':<24}{usd:>11,.2f}{'-':>11}"
         f"{over:>8}")
    emit(_row(replay.run(JULY_COUNTING)))
    emit(_row(replay.run(DR38)))


def _policy(a):
    p = DR38
    if a.envelope is not None:
        p = replace(p, name=f"DR-38.1, envelope ${a.envelope:g}",
                    envelope_usd=a.envelope)
    if a.loop_day is not None:
        p = replace(p, loops=tuple(
            replace(b, loop_day_usd=a.loop_day)
            if b.loop == "waiver-watch" else b for b in p.loops))
    return p


def part_policy(a) -> None:
    p = _policy(a)
    emit(f"== {p.name}: the storm at the gateway ==")
    for b in p.loops:
        emit(f"{b.loop:<14} run ${b.run_usd:.2f}/{b.run_steps} steps,"
             f" day ${b.loop_day_usd:,.2f}")
    emit(f"envelope ${p.envelope_usd:,.2f}; page {p.alert:.0%}, stop "
         f"100%; unknown usage at {p.unknown}")
    r = replay.run(p)
    for t, what, key in r.events:
        emit(f"{t:%a %H:%M}  {what:<9} {key}")
    emit(f"waiver watch billed ${r.billed:,.2f} in {r.calls:,} calls;"
         f" {r.refused:,} refused")
    emit(f"fare watch billed ${r.fare_billed:.2f}; runs refused "
         f"{r.fare_refused:,}")
    emit(f"servicing minutes over the shared limit: "
         f"{r.servicing_429_min}")


def part_chargeback(a) -> None:
    if a.by == "use-case":
        emit(f"== customer operations by use case, {a.month} ==")
        for k, v in chargeback.by_use_case(a.month).items():
            emit(f"{k:<12}{v:>12,.2f}")
        return
    emit(f"== chargeback, {a.month}, rule: {a.rule} ==")
    emit(f"{'owner':<22}{'model':>11}{'incident':>11}{'platform':>10}"
         f"{'total':>11}")
    st = chargeback.statement(a.month, a.rule)
    for o, r in st.items():
        emit(f"{o:<22}{r['model']:>11,.2f}{r['incident']:>11,.2f}"
             f"{r['platform']:>10,.2f}{r['total']:>11,.2f}")
    emit(f"{'total':<22}{sum(r['total'] for r in st.values()):>43,.2f}")


def part_august(a) -> None:
    days = card.AUGUST_WAIVER_DAYS
    b = DR38.budget("waiver-watch")
    top = max(days)
    emit("== waiver watch in August under DR-38.1 ==")
    emit(f"days {len(days)}, spend ${sum(days):,.2f}, worst day "
         f"${top:.2f} (Aug {days.index(top) + 1})")
    emit(f"1.2 replay worst day before launch ${card.REPLAY_WORST_DAY:.2f}")
    emit(f"page at ${b.loop_day_usd * DR38.alert:.2f}: "
         f"{sum(d >= b.loop_day_usd * DR38.alert for d in days)} days;"
         f" stop at ${b.loop_day_usd:.2f}: "
         f"{sum(d >= b.loop_day_usd for d in days)} days")
    emit(f"July's $10.00 day would have stopped "
         f"{sum(d >= 10 for d in days)} of {len(days)} days")
    emit(f"invoice: ${bill.total('August'):,.2f}; agent path "
         f"{outcome.close('August').verified:,} verified")


def part_card(a) -> None:
    emit("== economics card, filed Tuesday, September 8, 2026 ==")
    for name, value, note, owner in card.cells():
        emit(f"{name:<26}{value:>6}  {note:<22} {owner}")


PARTS = {"invoice": part_invoice, "close": part_close,
         "kinds": part_kinds, "weekly": part_weekly,
         "bound": part_bound, "storm": part_storm,
         "policy": part_policy, "chargeback": part_chargeback,
         "august": part_august, "card": part_card}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="economics.demo")
    ap.add_argument("--part", choices=sorted(PARTS))
    ap.add_argument("--rule", choices=("pool", "identity"),
                    default=None)
    ap.add_argument("--month", choices=("July", "August"),
                    default=None)
    ap.add_argument("--envelope", type=float)
    ap.add_argument("--loop-day", type=float)
    ap.add_argument("--by", choices=("owner", "use-case"),
                    default="owner")
    a = ap.parse_args(argv)
    parts = [a.part] if a.part else list(PARTS)
    for i, p in enumerate(parts):
        ns = argparse.Namespace(**vars(a))
        if ns.rule is None:
            ns.rule = "identity" if p == "chargeback" else "pool"
        if ns.month is None:
            ns.month = "August" if p == "chargeback" and \
                ns.by == "use-case" else "July"
        if i:
            emit()
        PARTS[p](ns)


if __name__ == "__main__":
    main()
