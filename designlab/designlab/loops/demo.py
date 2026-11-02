"""Chapter 28 demo: the fare watch as an unattended loop.

    python3 -m loops.demo                     # every part
    python3 -m loops.demo --part lint
    python3 -m loops.demo --part budget --day-usd 5
    python3 -m loops.demo --part state --state memory
    python3 -m loops.demo --part verify --self-verify

Offline, seeded, fixed Chicago clock. The model's comparability
judgment is simulated; no model call and no key.
"""
from __future__ import annotations

import argparse
from collections import Counter

from common.text import emit

from . import scenarios as S
from .fare_watch import V100, V101, V110, SelfCheck, Verifier, Actor
from .lint import PROPS, lint, passed
from .spec import (FARE_WATCH, WAIVER_WATCH, fare_watch_v0, model_stop,
                   no_state, self_verify)
from .trigger import Triggers
from .state import Persisted
from .world import ACTOR, at, fare_world
from dataclasses import replace


def hm(hr: int, minute: float = 0.0) -> str:
    return at(hr, minute).strftime("%H:%M")


def part_lint() -> None:
    emit("== the loop linter: seven properties, checked from the spec ==")
    emit("loop               " + " ".join(p[:5].ljust(5) for p in PROPS)
         + "  pass")
    specs = (("fare-watch 1.0.0", fare_watch_v0()),
             ("fare-watch 1.1.0", FARE_WATCH),
             ("waiver-watch", WAIVER_WATCH),
             ("inject model stop", model_stop(FARE_WATCH)),
             ("inject no state", no_state(FARE_WATCH)),
             ("inject self-verify", self_verify(FARE_WATCH)))
    for name, spec in specs:
        res = {f.prop: f.ok for f in lint(spec)}
        cells = " ".join(("ok" if res[p] else "FAIL").ljust(5)
                         for p in PROPS)
        emit(f"{name:18} {cells}  {passed(spec)} of 7")
    emit("findings for fare-watch 1.0.0:")
    for f in lint(fare_watch_v0()):
        if not f.ok:
            emit(f"  {f.prop:8} {f.why}"[:70])


def part_opening(self_verify_: bool = False) -> None:
    emit("== Sunday, June 14: fare watch 1.0.0, hour by hour ==")
    r = S.opening()
    fw = r["fw"]
    checker = SelfCheck(fw) if self_verify_ else None
    emit("hour   model report" + " " * 32 + "dash   verifier")
    for hr, h, v in r["rows"]:
        if checker is not None:
            v = checker.check_hour(hr, h, None)
        if hr % 6 == 0 or hr == S.JUNE14 + 14:
            emit(f"{hm(hr)}  {h.report:42}  green  "
                 f"{'green' if v['green'] else 'RED'}")
    reads = Counter()
    fields = Counter()
    for ln in fw.w.trail.lines:
        if '"loop:fare-watch"' in ln:
            reads["allowed" if '"allowed"' in ln else "refused"] += 1
            if '"invalid_arguments"' in ln:
                fields["invalid_arguments"] += 1
    emit(f"trail, loop:fare-watch: allowed {reads['allowed']:,}  "
         f"refused {reads['refused']:,}")
    emit(f"  refused as invalid_arguments: "
         f"{fields['invalid_arguments']:,}")
    w = fw.list[0]
    g = fw.w.gateway.call(ACTOR, "offers", "offers_search",
                          {"booking_ref": w.booking,
                           "segment": str(w.segment), "kind": "flight"})
    emit(f"  one replayed: {g.reason}, field {g.field}")
    first = r["rows"][0][2]
    if checker is None:
        emit(f"verifier, 00:00 hour: {'; '.join(first['why'])}"[:70])
    else:
        emit("self-check: every hour agrees with itself")
    m = S.missed()
    usd = sum(x[2] for x in m["vouchers"])
    emit(f"owed June 12 to June 15 10:00: {len(m['vouchers'])} vouchers "
         f"${usd:,.2f}")
    emit(f"  plus {len(m['handoffs'])} hand-offs over the $100 cap")
    by = {w.wid: w for w in fw.list}
    for hr, wid, amt, f in m["vouchers"]:
        if wid == "W-1208":
            w = by[wid]
            emit(f"  {wid} {w.booking} {w.flight} booked "
                 f"${w.booked:.2f}")
            emit(f"  {hm(hr)} Sunday fare ${f:.2f}, owed ${amt:.2f}")


def part_triggers() -> None:
    emit("== triggers: one filing republished overnight, June 17-18 ==")
    w = S.night_watch()
    emit(f"watch {w.wid}, booked ${w.booked:.2f}, basic-economy "
         "fare below floor")
    emit("build               wakes  runs  model calls  stop")
    rows = (("1.0.1", V101, False),
            ("1.0.1 + run key", V101, True),
            ("1.1.0", V110, True))
    for name, d, dd in rows:
        r = S.night(d, dd)
        stop = r["stalls"][0][1] if r["stalls"] else "none"
        emit(f"{name:18} {r['wakes']:6} {r['runs']:5} "
             f"{r['model_calls']:12}  {stop}")
    emit("-- a durable timer fires once, with two sweepers --")
    rs = Persisted().rs
    t1, t2 = Triggers(rs, "fare-watch"), Triggers(rs, "fare-watch")
    for hr in range(24):
        t1.schedule(f"sweep@{hm(hr)}", at(hr))
    got = Counter()
    for hr in range(24):
        for name, t in (("a", t1), ("b", t2)):
            got[name] += len(t.due(at(hr, 0.1)))
    emit(f"24 sweeps set; sweeper a fired {got['a']}, "
         f"sweeper b fired {got['b']}")


def part_stops() -> None:
    emit("== stop conditions: 40 injected stalls ==")
    inj = S.injections()
    for kind, label in (("repeat", "same verdict, not saved"),
                        ("swing", "verdict cache of one")):
        st = inj[kind]
        stopped = sum(1 for x in st if x)
        emit(f"{label:24} stopped {stopped} of {len(st)}, "
             f"max steps {max(st)}")
    r = S.night(replace(V101, version="1.0.1+d", detector=True), False)
    emit(f"June 17-18 night with the detector: stopped after "
         f"{r['model_calls']} calls")
    emit(f"  watch status {r['status']}, cost ${r['usd']:.4f}")
    t = [x for x in r["fw"].w.trail.lines if '"stall"' in x]
    emit(f"  trail entries for the stall: {len(t)}")


def part_state(kind: str) -> None:
    emit(f"== persisted state: two days, worker restart every 6 h, "
         f"{kind} ==")
    r = S.replay(days=2, store_kind=kind, restart_every=6)
    vouchers = sum(d["vouchers"] for d in r["days"].values())
    usd = sum(d["voucher_usd"] for d in r["days"].values())
    red = sum(d["hours"] - d["green"] for d in r["days"].values())
    calls = sum(d["calls"] for d in r["days"].values())
    emit(f"vouchers {vouchers}  ${usd:,.2f}  model calls {calls}  "
         f"red hours {red}")
    wrong = 0
    for _hr, _h, v in r["hours"]:
        for why in v["why"]:
            if why.startswith("vouchers "):
                wrong += int(why.split()[1])
    emit(f"vouchers the verifier re-derived as wrong: {wrong}")


def part_verify() -> None:
    emit("== verification: the actor's report against the trail ==")
    for name, d in (("1.0.0", V100), ("1.1.0", V110)):
        fw = fare_world()
        a = Actor(fw, d)
        v = Verifier(fw)
        h = a.run_hour(S.JUNE14 + 12)
        r = v.check_hour(S.JUNE14 + 12, h, a.store)
        emit(f"{name}: claimed {h.claimed:,}  trail {r['trail_reads']:,}"
             f"  sample {r['sample']}  "
             f"{'green' if r['green'] else 'RED'}")
        for why in r["why"]:
            emit(f"  {why}")


def part_budget(day_usd: float | None) -> dict:
    if day_usd is None:
        emit("== loop runs against budget, June 12 to 28, 1.1.0 ==")
        r = S.replay()
    else:
        emit(f"== try it: fare-watch loop day at ${day_usd:.2f}, "
             "June 16 to 17 ==")
        r = S.replay(days=2, first_day=4, loop_day=day_usd)
    emit("day     runs    calls  spend   vouchers  voucher $  hand-offs")
    for day, d in r["days"].items():
        emit(f"{day[5:]}  {d['runs']:6,}  {d['calls']:5}  "
             f"${d['usd']:5.2f}  {d['vouchers']:8}  "
             f"{d['voucher_usd']:9,.2f}  {d['handoffs']:9}")
    tot = sum(d["usd"] + d["waiver_usd"] for d in r["days"].values())
    runs = sum(d["runs"] for d in r["days"].values())
    emit(f"loop runs {runs:,}  model spend ${tot:,.2f}")
    emit(f"runs past budget: {len(r['runs_over'])}  scopes over: "
         f"{len(r['enf'].over())}")
    stops = Counter(e["stop"] for e in r["enf"].log if "stop" in e)
    alerts = [e["alert"] for e in r["enf"].log if "alert" in e]
    emit(f"refusals by scope: {dict(stops) or 'none'}")
    for a in alerts:
        emit(f"  80% alert: {a}")
    for d, d_ in r["days"].items():
        if d_["first_stop"] is not None:
            emit(f"  {d}: first refusal in the {hm(d_['first_stop'])} "
                 f"sweep, {d_['stops']} refused")
    return r


def part_change() -> None:
    emit("== restricted change: what the loop's identity may do ==")
    fw = fare_world(10)
    g = fw.w.gateway
    w = fw.list[0]
    tries = (
        ("refund_ticket", "payments", "refund_ticket",
         {"itinerary_id": w.booking}, None),
        ("voucher, no permission", "payments", "voucher_issue",
         {"itinerary_id": w.booking, "amount_usd": "40.00",
          "reason": "service"}, None),
    )
    for label, srv, tool, args, pid in tries:
        r = g.call(ACTOR, srv, tool, args, permission=pid)
        emit(f"{label:24} {'allowed' if r.ok else r.reason}")
    from .fare_watch import Control
    c = Control(fw)
    args = {"itinerary_id": w.booking, "amount_usd": "40.00",
            "reason": "service"}
    pid = c.permit("voucher_issue", args)
    r1 = g.call(ACTOR, "payments", "voucher_issue", args, permission=pid)
    r2 = g.call(ACTOR, "payments", "voucher_issue", args, permission=pid)
    emit(f"{'voucher, permission':24} {'allowed' if r1.ok else r1.reason}")
    emit(f"{'same permission again':24} {'allowed' if r2.ok else r2.reason}")
    bigger = dict(args, amount_usd="90.00")
    r3 = g.call(ACTOR, "payments", "voucher_issue", bigger,
                permission=c.permit("voucher_issue", args))
    emit(f"{'amount changed after':24} {'allowed' if r3.ok else r3.reason}")
    emit(f"{'control, $128.35':24} {c.voucher('2026-06-14', 128.35)}")


def part_human(r: dict) -> None:
    emit("== the human on the loop: where each signal went, June 12-28 ==")
    pages = [("voucher day 80%", f"{d} {t}") for d, t in
             r["control"].alerts]
    pages += [("loop day 80%", e["alert"]) for e in r["enf"].log
              if "alert" in e]
    red = [(hr, v) for hr, h, v in r["hours"] if not v["green"]]
    queue = Counter()
    for _hr, h, _v in r["hours"]:
        queue["hand-off to the desk"] += len(h.handoffs)
        queue["stall paused"] += len(h.stalls)
        queue["budget refusal"] += len(h.budget_stops)
    emit(f"pages to the owner: {len(pages)}")
    for kind, when in pages:
        emit(f"  {kind}: {when}")
    emit(f"verifier red hours: {len(red)} of {len(r['hours'])}")
    emit("morning queue:")
    for k, n in queue.items():
        emit(f"  {k:22} {n}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="all")
    ap.add_argument("--day-usd", type=float, default=None)
    ap.add_argument("--state", default="run_store",
                    choices=("run_store", "memory"))
    ap.add_argument("--self-verify", action="store_true")
    a = ap.parse_args(argv)
    p = a.part
    if p in ("all", "lint"):
        part_lint()
    if p in ("all", "opening"):
        part_opening(a.self_verify)
    if p in ("all", "triggers"):
        part_triggers()
    if p in ("all", "stops"):
        part_stops()
    if p in ("all", "state"):
        part_state(a.state)
    if p in ("all", "verify"):
        if a.self_verify:
            part_opening(True)
        else:
            part_verify()
    r = None
    if p in ("all", "budget"):
        r = part_budget(a.day_usd)
    if p in ("all", "change"):
        part_change()
    if p in ("all", "human"):
        part_human(r if r is not None else S.replay())


if __name__ == "__main__":
    main()
