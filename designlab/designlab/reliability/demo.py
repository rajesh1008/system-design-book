"""Chapter 37 demo: objectives, budgets, incidents, and runbooks.

    python3 -m reliability.demo                         # every part
    python3 -m reliability.demo --part objectives       # July 8 window
    python3 -m reliability.demo --part objectives --uptime-only
    python3 -m reliability.demo --part alerts [--pinned]
    python3 -m reliability.demo --part budget [--extra 20] [--pinned]
    python3 -m reliability.demo --part storm
    python3 -m reliability.demo --part stop --incident july8
    python3 -m reliability.demo --part stop --incident storm \
        [--tier3-first | --tier2-only]
    python3 -m reliability.demo --part stop --incident effect --at 12
    python3 -m reliability.demo --part gameday [--fixed]
    python3 -m reliability.demo --part runbook [--old]
    python3 -m reliability.demo --part review
    python3 -m reliability.demo --part card

Offline, seeded (37), Chicago clock (CDT). No model call and no key.
The records are synthetic; Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
from datetime import date

from common.text import emit

from . import (budget, burn, card, daily, gameday, july8, review,
               runbook, stop, storm)
from .objectives import BY_KEY, FIVE, UPTIME, Reading, read, read_all
from .records import at, hm

KINDS = july8.KINDS


def fmt(r) -> str:
    if r.status == "unknown":
        return f"{r.key:<22} unknown   {r.note}"[:70]
    if r.key.startswith("unauthorized"):
        return f"{r.key:<22} {r.bad:>7}       0  bad {r.bad:>3}  " + \
            ("met" if not r.bad else "MISSED")
    target = BY_KEY.get(r.key.split(":")[0].split(" ")[0], UPTIME).target
    state = "met" if r.rate >= target else "MISSED"
    return (f"{r.key:<22} {r.rate:>7.2%} {target:>7.2%}  bad "
            f"{r.bad:>3}  {state}")


def part_objectives(a) -> list[str]:
    rec = july8.build(pinned=a.pinned)
    s, e = july8.MOVED, july8.STOPPED
    out = [f"July 8, {hm(s)} to {hm(e)} CDT; "
           f"{len(rec.tasks):,} agent tasks"]
    objs = (UPTIME,) if a.uptime_only else (UPTIME,) + FIVE
    out.append(f"{'objective':<22} {'reading':>7} {'target':>7}")
    for r in read_all(objs, rec, s, e, kinds=KINDS):
        if r.key == "verified:" + KINDS[0]:
            whole = read(BY_KEY["verified"], rec, s, e)
            whole.key = "verified (all kinds)"
            out.append(fmt(whole))
        out.append(fmt(r))
    return out


def part_alerts(a) -> list[str]:
    rec = july8.build(pinned=a.pinned)
    s, e = july8.MOVED, july8.STOPPED
    out = [f"July 8 replay, classifier {'pinned' if a.pinned else 'as run'}"]
    for obj, kind in ((UPTIME, ""), (BY_KEY["verified"], ""),
                      (BY_KEY["verified"], "rebooking")):
        name = obj.key + (f":{kind}" if kind else "")
        al = burn.scan(obj, rec.tasks, s, e, kind=kind or None)
        if not al:
            out.append(f"{name:<20} no alert")
        for x in al:
            out.append(f"{name:<20} {x.rule:<6} {hm(x.at)}  long "
                       f"{x.long_burn:4.1f}x  bad {x.bad_in_long}")
    flag = july8.first_code_flag(rec)
    out.append(f"{'code check':<20} " +
               (f"first hold {hm(flag[0].ended)}" if flag[0] else "no hold"))
    out.append(f"{'desk lead saw':<20} {hm(july8.DESK_SAW)}")
    return out


def part_budget(a) -> list[str]:
    rows = daily.series(pinned=a.pinned)
    if a.extra:
        rows = [(d, n, b + (a.extra if d == date(2026, 7, 9) else 0))
                for d, n, b in rows]
    out = ["rebooking slice, verified outcomes 99.0%, 28 days"]
    for d in (date(2026, 7, 7), date(2026, 7, 8), date(2026, 7, 9),
              date(2026, 7, 20), date(2026, 8, 31)):
        _, n, bad, bud, used = daily.on(rows, d)
        dec = budget.decide(Reading("verified:rebooking", n - bad, n,
                                    bud, bad, "met"))
        out.append(f"{d:%b %d}  {n:>6,} tasks  bad {bad:>3} of "
                   f"{bud:5.1f}  {used:>6.1%}  {dec.state}")
    if a.extra:
        out.append(f"(+{a.extra} unverified added on July 9)")
    return out


def part_storm(a) -> list[str]:
    st = storm.simulate()
    page = burn.scan(BY_KEY["latency"], st.records.tasks, storm.START,
                     storm.END)
    first_page = next(x for x in page if x.rule == "page")
    lim = st.first_limited()
    out = [f"waiver watch storm from Sat {hm(storm.START)} CDT",
           f"loop calls billed by provider {st.billed():>10,}",
           f"loop calls counted by enforcer {st.counted():>9,}",
           f"chains running at the end {st.minutes[-1].chains:>14,}",
           f"first 429 to servicing         Sun {hm(lim)}",
           f"task latency page              Sun {hm(first_page.at)}",
           f"hours with no objective red    "
           f"{storm.hidden_hours(st, first_page.at):.1f}"]
    t = gameday.usage_page(st)
    out.append(f"with the provider-count alert  Sat {hm(t)}")
    out.append(f"billed, no scheduler requeue    "
               f"{storm.simulate(requeue=False).billed():>8,}")
    out.append(f"billed, retries in one layer    "
               f"{storm.simulate(harness=1, requeue=False).billed():>8,}")
    return out


def part_stop(a) -> list[str]:
    if a.incident == "july8":
        s = stop.july8()
    elif a.incident == "storm":
        pulls = None
        if a.tier3_first:
            pulls = [(9, 3, "lena.okafor", "loop spend")]
        elif a.tier2_only:
            pulls = [(9, 2, "lena.okafor", "loop spend")]
        s = stop.storm(pulls)
    else:
        s = gameday_effect_stop(a.at)
    return [f"stop: {s.name}"] + stop.lines(s)


def gameday_effect_stop(after: int):
    t = at("2026-08-18", "10:02")
    return stop.run_stop("injected unauthorized effect", t,
                         [(after, 2, "game.day", "")], "agent:servicing",
                         "refund_ticket", "effect", 8.0,
                         "kill/servicing")


def part_gameday(a) -> list[str]:
    res = gameday.run(legacy=not a.fixed)
    out = ["game day, Tuesday, August 18, 2026" +
           (" (rerun after fix)" if a.fixed else "")]
    for r in res:
        out.append(f"{r.key} {'held' if r.held else 'FALSIFIED'}: "
                   f"{r.hypothesis}"[:70])
        out.append(f"   measured: {r.measured}"[:70])
    out.append(f"{len(res)} hypotheses, "
               f"{sum(not r.held for r in res)} falsified")
    return out


def part_runbook(a) -> list[str]:
    books = (runbook.OLD,) if a.old else runbook.RUNBOOKS
    out = []
    for rb in books:
        if not a.old:
            out += runbook.render(rb)
        problems = runbook.lint(rb, failing="model gateway")
        out.append(f"lint {rb.key}: " +
                   ("clean" if not problems else f"{len(problems)} "
                    "problems"))
        out += [f"  {p}" for p in problems]
    return out


def part_review(a) -> list[str]:
    out = []
    for r in review.REVIEWS:
        out.append(f"{r.incident} (review {r.held_on})"[:70])
        for k in ("time to detect", "time to stop", "affected"):
            out.append(f"  {k:<15} {r.numbers[k]}"[:70])
        out.append(f"  actions {len(r.actions)}, owners "
                   f"{len({x.owner for x in r.actions})}, hand-offs "
                   f"{len(r.handoffs)}")
        g = review.gate(r)
        out.append("  gate: " + ("closed" if not g else "; ".join(g)))
    return out


def part_card(a) -> list[str]:
    out = ["reliability card, Monday, August 31, 2026"]
    for k, v, who in card.card():
        out.append(f"{k:<13} {v}"[:70])
        out.append(f"{'':<13} answers: {who}")
    return out


PARTS = {"objectives": part_objectives, "alerts": part_alerts,
         "budget": part_budget, "storm": part_storm, "stop": part_stop,
         "gameday": part_gameday, "runbook": part_runbook,
         "review": part_review, "card": part_card}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=sorted(PARTS))
    ap.add_argument("--uptime-only", action="store_true")
    ap.add_argument("--pinned", action="store_true")
    ap.add_argument("--extra", type=int, default=0)
    ap.add_argument("--incident", default="july8",
                    choices=("july8", "storm", "effect"))
    ap.add_argument("--tier3-first", action="store_true")
    ap.add_argument("--tier2-only", action="store_true")
    ap.add_argument("--at", type=int, default=12)
    ap.add_argument("--fixed", action="store_true")
    ap.add_argument("--old", action="store_true")
    a = ap.parse_args(argv)
    parts = [a.part] if a.part else list(PARTS)
    for i, p in enumerate(parts):
        if i:
            emit("")
        for ln in PARTS[p](a):
            emit(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
