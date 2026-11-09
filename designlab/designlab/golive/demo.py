"""Chapter 44 demo: the go-live and the storm day, replayed.

    python3 -m golive.demo --part pilot
    python3 -m golive.demo --part ramp
    python3 -m golive.demo --part day
    python3 -m golive.demo --part replay [--scenario NAME]
        [--order fare] [--no-emergency] [--widen 1000]
    python3 -m golive.demo --part compare
    python3 -m golive.demo --part record
    python3 -m golive.demo --part capacity
    python3 -m golive.demo --part recovery
    python3 -m golive.demo --part card

Offline; no model call and no key.
"""
from __future__ import annotations

import argparse

from capacity.approvals import drain_hours, offered, seats_for
from common.text import emit
from corpus.generate import PERSON_COST_USD

from . import pilot, ramp, record, review
from .day import CLOSE, REOPEN, STORM_CHANGES, clock, generate, in_window
from .replay import (SCENARIOS, SEATED_ROTA, latency_at,
                     latency_while_newest, run, t, variant)

ERR_EXPECTED, ERR_REVERSE = 0.003, 0.005
SERVICE_MIX = 3.4          # minutes a card on the evening desk


def part_pilot() -> None:
    emit("== the pilot and its numbers ==")
    for line in pilot.lines():
        emit(line)


def part_ramp() -> None:
    emit("== the ramp by task type ==")
    for line in ramp.ramp_lines():
        emit(line)
    emit()
    emit("June review, each autonomous type on its own gate:")
    for g in ramp.gates({"R1", "V1"}):
        emit(f"  {g.kind}  {g.verified_28d:.1%}  {g.why_not()}")
    emit()
    emit("the same month as a ramp by share of traffic:")
    v = ramp.traffic_verified({"R1", "V1"})
    emit(f"  blended verified {v:.2%}: the gate holds every type")
    v2 = ramp.traffic_verified({"R1", "V1", "C1"})
    emit(f"  with C1 tuned too {v2:.2%}: the gate opens every type,")
    emit("  U1 at 96.8% included")
    p = ramp.traffic_hold_at({"R1", "V1"})
    emit(f"  desk backlog passes 50 at a {p:.0%} traffic share")


def part_day() -> None:
    cs = generate()
    emit("== the storm day, synthetic records ==")
    emit(f"changes 6:00 a.m. to midnight  {len(cs):,}")
    emit(f"inside the closure, {clock(CLOSE)} to {clock(REOPEN)}  "
         f"{in_window(cs):,}")
    cards = sum(1 for c in cs if c.card and CLOSE <= c.t < REOPEN)
    emit(f"of which need a person's approval  {cards:,}")
    assert in_window(cs) == STORM_CHANGES


def _scenario(a):
    kw, names = {}, []
    if a.order:
        kw["switch_to"] = a.order
        names.append(f"{a.order}-order")
    if a.no_emergency:
        kw["emergency_at"] = None
        names.append("no-emergency")
    if a.widen:
        kw["surge_limit_usd"] = float(a.widen)
        names.append(f"widen-{a.widen}")
    if kw:
        return variant("+".join(names), **kw)
    return SCENARIOS[a.scenario]


def show(r) -> None:
    s = r.scenario
    emit(f"== replay: {s.name} ==")
    emit(f"budget page {clock(r.paged_at) if r.paged_at else '-'};"
         f" spent {clock(r.budget_spent_at) if r.budget_spent_at else '-'}"
         f"; to people at intake {r.to_people:,}")
    emit(f"queue peak {r.peak_depth:,} at {clock(r.peak_at)}; oldest "
         f"card {r.oldest_at_peak:.0f} min")
    emit(f"latency while newest first: "
         f"{latency_while_newest(r):.0f} min")
    if r.cleared_at:
        emit(f"cleared (under 50) {clock(r.cleared_at)}, "
             f"{r.hours_to_clear:.1f} h after declaring")
    else:
        emit("not cleared before Friday morning")
    emit(f"missed departures {r.missed} ({r.missed_by_peak} by the "
         "peak)")
    emit(f"held by tier two {r.held:,}; done "
         f"{clock(r.held_done_at) if r.held_done_at else '-'}")
    emit(f"surge rule decided {r.surge_cards:,}, ${r.surge_usd:,.0f}")
    emit(f"verified outcomes on the day {r.verified_rate:.2%}")


def part_replay(a) -> None:
    r = run(_scenario(a))
    show(r)
    if a.widen:
        lo = r.surge_usd * ERR_EXPECTED
        hi = r.surge_usd * ERR_REVERSE
        emit(f"at 0.3% error: ${lo:,.0f} paid wrongly; at the 0.5% "
             f"line: ${hi:,.0f}")
        emit(f"largest refund with no person: ${r.surge_max_usd:,.0f}")


def _clear(r) -> str:
    if r.cleared_at is None:
        return "not by Fri"
    if r.cleared_at >= 24 * 60:
        return "Fri " + clock(r.cleared_at).split()[0]
    return clock(r.cleared_at)


def part_compare() -> None:
    emit("== scenarios ==")
    emit(f"{'scenario':<16}{'peak':>6}{'at':>11}{'clear':>12}"
         f"{'missed':>7}{'verif':>8}")
    for name in ("as-run", "no-priority", "no-tier2", "fare",
                 "no-emergency", "widen-1000", "redesigned",
                 "redesigned-rota"):
        r = run(name)
        clear = _clear(r)
        emit(f"{name:<16}{r.peak_depth:>6,}{clock(r.peak_at):>11}"
             f"{clear[:11]:>12}{r.missed:>7}{r.verified_rate:>8.2%}")
    r = run("no-emergency")
    emit(f"no-emergency sent {r.to_people:,} chats to people at intake,")
    emit(f"  ${r.to_people * PERSON_COST_USD:,.0f} at the person "
         "baseline")


LEVERS = (
    ("order at 11:40", dict(switch_at=t(11, 40))),
    ("reserve at 11:40", dict(emergency_at=t(11, 40))),
    ("tier two at 11:40", dict(tier2_at=t(11, 40))),
    ("rule at 12:10", dict(surge_at=t(12, 10))),
    ("rota to 7 p.m.", dict(seated=SEATED_ROTA)),
)


def part_levers() -> None:
    """Each redesigned decision alone, the rest as it ran."""
    emit("== one lever at a time ==")
    emit(f"{'lever':<18}{'peak':>6}{'at':>11}{'clear':>12}"
         f"{'missed':>7}")
    for name, kw in LEVERS:
        r = run(variant(name, **kw))
        emit(f"{name:<18}{r.peak_depth:>6,}{clock(r.peak_at):>11}"
             f"{_clear(r):>12}{r.missed:>7}")


def part_record() -> None:
    emit("== the incident record ==")
    for line in record.lines():
        emit(line)
    emit(f"spans in the record trace: {len(record.spans())}")


def part_capacity() -> None:
    emit("== the approval desk, sized ==")
    cs = generate()
    hour = [c for c in cs if t(12) <= c.t < t(13)]
    ref = sum(1 for c in hour if c.card and c.kind != "rebook_card")
    reb = sum(1 for c in hour if c.kind == "rebook_card")
    emit(f"12:00 to 1:00 p.m.: {len(hour):,} changes")
    emit(f"  refund and credit cards {ref:,} at 2 min: "
         f"{offered(ref, 2):.0f} busy;")
    emit(f"  seats for 95% inside 60 min: {seats_for(ref, 2, 60)}")
    emit(f"  rebooking cards {reb:,} at 5 min; seats for 30 min: "
         f"{seats_for(reb, 5, 30)}")
    emit(f"Chapter 43's average storm hour, 2,238 refunds: "
         f"{seats_for(2238, 2, 60)} seats")
    r = run("as-run")
    back = [d for m, d in r.depth if m == t(17)][0]
    inflow = sum(n for m, n in r.inflow.items()
                 if t(17) <= m < t(22)) / 5
    emit("as run: 62 seated at 3:00 p.m., 16 from 5:00 p.m.")
    emit(f"backlog at 5:00 p.m. {back:,}; cards in {inflow:,.0f}/h "
         "to 10 p.m.")
    for seats in (16, 30):
        h = drain_hours(back, seats, SERVICE_MIX, inflow)
        emit(f"  {seats} seats at {SERVICE_MIX} min a card: drains in "
             f"{h:.1f} h")


def part_recovery() -> None:
    emit("== recovery: verified outcomes by day ==")
    series = review.daily_verified()
    for d, v in series:
        bar = "#" * max(0, round((v - 0.985) * 4000))
        emit(f"Sept {d:>2}  {v:.2%}  {bar}")
    emit(f"back at 99.5%: Sept {review.recovered_on(series)}")


def part_card() -> None:
    for line in review.card_lines():
        emit(line)
    emit()
    for line in review.design_lines():
        emit(line)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="golive.demo")
    p.add_argument("--part", required=True,
                   choices=["pilot", "ramp", "day", "replay", "compare",
                            "levers", "record", "capacity", "recovery",
                            "card"])
    p.add_argument("--scenario", default="as-run",
                   choices=sorted(SCENARIOS))
    p.add_argument("--order", choices=["newest", "oldest", "departure",
                                       "fare"])
    p.add_argument("--no-emergency", action="store_true")
    p.add_argument("--widen", type=int)
    a = p.parse_args(argv)
    if a.part == "replay":
        part_replay(a)
    else:
        {"pilot": part_pilot, "ramp": part_ramp, "day": part_day,
         "compare": part_compare, "levers": part_levers,
         "record": part_record,
         "capacity": part_capacity, "recovery": part_recovery,
         "card": part_card}[a.part]()


if __name__ == "__main__":
    main()
