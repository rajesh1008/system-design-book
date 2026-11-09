"""Chapter 41 demo: the charter, the gap, the matrix, the scenarios.

    python3 -m org.demo                          # every part
    python3 -m org.demo --part charter
    python3 -m org.demo --part roster
    python3 -m org.demo --part gap [--hire june|architect]
    python3 -m org.demo --part matrix
    python3 -m org.demo --part scenarios [--matrix 2026-08-19]
    python3 -m org.demo --part scenarios --fault no-owner|no-key
    python3 -m org.demo --part scenarios --without "Rachel Morgan"
    python3 -m org.demo --part scenarios --owner release="Hannah Clarke"
    python3 -m org.demo --part scenarios --seventh
    python3 -m org.demo --part stall
    python3 -m org.demo --part rhythm
    python3 -m org.demo --part market
    python3 -m org.demo --part card

Offline and deterministic. No model call and no key.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
from datetime import date

from bank import market
from common.text import emit

from . import rights
from .card import CHARTER, card
from .rhythm import FORUMS, stall_cost, stalled, unreviewed, weekly_hours
from .roles import AS_OF, JUNE_REQ, PARTNERS, SEATS
from .skills import SKILLS, coverage, gaps, with_seat

PARTS = ("charter", "roster", "gap", "matrix", "scenarios", "stall",
         "rhythm", "market", "card")
SHORT = {"distributed": "dist", "models": "model", "retrieval": "retr",
         "control": "ctrl", "evaluation": "eval", "operations": "ops"}


def part_charter(a) -> None:
    for line in CHARTER:
        emit(line)


def part_roster(a) -> None:
    emit(f"== seats as of {AS_OF:%B} {AS_OF.day}, {AS_OF.year} ==")
    for s in SEATS:
        when = (f"starts {s.starts:%b} {s.starts.day}" if s.starts
                else "seated")
        emit(f"{s.holder:<26}{s.plane:<11}{when}")
    emit(f"== partners (not headcount) ==")
    for p in PARTNERS:
        emit(f"{p.name:<17}{p.function}")


def part_gap(a) -> None:
    seats = SEATS
    label = "both hires seated"
    if a.hire == "june":
        seats = with_seat(JUNE_REQ)
        label = "June requisition instead"
    day = AS_OF if a.hire is None else date(2026, 9, 14)
    if a.hire is None:
        label = "seated on Aug 31"
    cov = coverage(day, seats)
    emit(f"== skills at level 2+, lead excluded: {label} ==")
    emit(f"{'skill':<12}{'n':>3}  holders")
    for k in SKILLS:
        names = ", ".join(h.replace(" engineer ", " eng ")
                          for h in cov[k])
        if len(names) > 52:
            names = names[:49] + "..."
        emit(f"{k:<12}{len(cov[k]):>3}  {names}")
    g = gaps(day, seats)
    emit(f"gaps (fewer than 2): {', '.join(g) or 'none'}")


def part_matrix(a) -> None:
    emit("== decision-rights matrix, signed 2026-08-21 ==")
    emit(f"{'decision':<17}{'owner':<20}{'deputy':<20}{'consult':>8}")
    for d in rights.SIGNED:
        dep = (d.deputy or "-").replace("evaluation engineer",
                                        "eval eng").replace(
            "platform engineer", "platform eng").replace(
            "operations duty manager", "ops duty manager")
        own = d.owners[0].replace("loyalty product owner",
                                  "loyalty owner")
        emit(f"{d.key:<17}{own:<20}{dep:<20}{len(d.consulted):>8}")
    own = rights.owners()
    top = max(own.items(), key=lambda x: len(x[1]))
    emit(f"{len(rights.SIGNED)} decisions, {len(own)} owners; "
         f"most held by one: {top[0]}, {len(top[1])}")


def _parse_owner(spec: str) -> tuple[str, str]:
    key, _, name = spec.partition("=")
    return key.strip(), name.strip().strip('"')


def part_scenarios(a) -> None:
    mdate = a.matrix
    matrix = rights.MATRICES[mdate]
    signers = rights.SIGNERS[mdate]
    partners = PARTNERS
    scenarios = rights.SCENARIOS
    day = None
    title = f"matrix {mdate}"
    if mdate == "2026-08-19":
        day = date(2026, 8, 19)
    if a.fault == "no-owner":
        matrix, signers = rights.AUG4, rights.SIGNERS["2026-08-04"]
        title = "fault: no owner for rebook rules (Aug 4)"
    elif a.fault == "no-key":
        signers = ("Rachel Morgan",)
        title = "fault: owner named, no signing key"
    if a.without:
        partners, gone = rights.without(a.without)
        title = f"without {', '.join(sorted(gone))}"
    if a.owner:
        key, name = _parse_owner(a.owner)
        matrix = rights.reassign(key, name, matrix)
        title = f"{key} owned by {name}"
    if a.seventh:
        scenarios = scenarios + (rights.SEVENTH,)
        title += ", seventh scenario"
    emit(f"== scenarios: {title} ==")
    results = rights.check_all(matrix, signers, scenarios, day,
                               SEATS, partners)
    for s, found in results:
        emit(f"{s.key:<17}{'PASS' if not found else 'FAIL':<6}"
             f"{s.title}")
        for f in found:
            emit(f"    {f.decision}: {f.problem}")
    ok = sum(1 for _, f in results if not f)
    walked = sum(len(s.needs) for s, _ in results)
    emit(f"{ok} of {len(results)} pass; {walked} decisions walked")


def part_stall(a) -> None:
    emit("== rebook-v3: work held at the desk, Aug 7 to Aug 16 ==")
    for d, n in stalled():
        emit(f"{d:%a %b} {d.day:<3}{n:>5}")
    days, n, usd = stall_cost()
    emit(f"{days} days, {n:,} rebookings at $6.20 assisted, not $1.61")
    emit(f"extra cost ${usd:,.2f}")


def part_rhythm(a) -> None:
    emit("== operating rhythm (CDT) ==")
    for f in FORUMS:
        emit(f"{f.name:<19}{f.when:<14}{f.owner:<17}{f.minutes:>4} min")
    emit(f"{weekly_hours():.1f} meeting hours a week across the forums")
    left = unreviewed()
    emit(f"decisions no forum reviews: {', '.join(left) or 'none'}")


def part_market(a) -> None:
    ps = market.load()
    emit(f"== postings: {len(ps)} from "
         f"{len({p.company for p in ps})} employers, Nov 2, 2026 ==")
    c = market.counts(ps)
    for t in market.TAGS:
        emit(f"{t:<12}{c[t]:>4}  {c[t] / len(ps):>4.0%}")
    both = market.both(ps, "control", "evaluation")
    emit(f"control and evaluation together: {len(both)}")
    for p in both:
        emit(f"  {p.company[:20]:<21}{p.title[:42]}")
    emit("by segment: postings, control, evaluation, median $K")
    for seg, group in sorted(market.segments(ps).items()):
        cc = market.counts(group)
        mid = market.midpoint_k(group)
        ms = f"{mid:>7.1f}" if mid else f"{'-':>7}"
        emit(f"  {seg:<12}{len(group):>4}{cc['control']:>5}"
             f"{cc['evaluation']:>5}{ms}")


def part_card(a) -> None:
    emit("== team card, August 2026 ==")
    for k, v in card().items():
        emit(f"{k:<20}{v}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--hire", choices=("june", "architect"))
    ap.add_argument("--matrix", default="2026-08-21",
                    choices=sorted(rights.MATRICES))
    ap.add_argument("--fault", choices=("no-owner", "no-key"))
    ap.add_argument("--without")
    ap.add_argument("--owner")
    ap.add_argument("--seventh", action="store_true")
    a = ap.parse_args(argv)
    parts = [a.part] if a.part else list(PARTS)
    for i, p in enumerate(parts):
        if i:
            emit()
        globals()[f"part_{p}"](a)


if __name__ == "__main__":
    main()
