"""The chapter's replays, each a function the demo and tests call."""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from .budget import LoopEnforcer
from .fare_watch import (V100, V101, V110, Actor, Control, Design,
                         Hour, Verifier, offer_digest)
from .spec import FARE_WATCH, WAIVER_WATCH
from .state import Memory, Persisted
from .trigger import Triggers
from .waiver import NOTICES, grant, run_notice
from .world import (WATCHES, Watch, at, day_of, fare, fare_world)

JUNE14 = 48                # hour index of Sunday, June 14, 00:00 CDT
FIX = 82                   # Monday, June 15, 10:00 a.m.: 1.0.1 ships


def opening(n: int = WATCHES) -> dict:
    """Sunday, June 14 under 1.0.0, with the June 15 verifier
    replayed over the same hours."""
    fw = fare_world(n)
    a = Actor(fw, V100)
    v = Verifier(fw)
    rows = []
    for hr in range(JUNE14, JUNE14 + 24):
        h = a.run_hour(hr)
        rows.append((hr, h, v.check_hour(hr, h, a.store)))
    return {"rows": rows, "fw": fw}


def missed(n: int = WATCHES, until: int = FIX) -> dict:
    """What 1.1.0 would have done from go-live to the fix."""
    fw = fare_world(n)
    a = Actor(fw, V110, enforcer=LoopEnforcer.for_specs(FARE_WATCH,
                                                        WAIVER_WATCH))
    vouchers, handoffs = [], []
    for hr in range(0, until):
        h = a.run_hour(hr)
        vouchers += [(hr, *x) for x in h.vouchers]
        handoffs += [(hr, *x) for x in h.handoffs]
    return {"vouchers": vouchers, "handoffs": handoffs}


def night_watch(n: int = WATCHES) -> Watch:
    """A watch whose flight showed a basic-economy fare below its
    floor through the early hours of Thursday, June 18."""
    for w in fare_world(n).list:
        f, cabin = fare(w, 144)
        if cabin == "basic" and f <= w.booked - 5:
            return w
    raise LookupError("no night watch")


def night(design: Design, dedupe: bool, n: int = WATCHES) -> dict:
    """The night of June 17 to 18: an hourly sweep and 35 republished
    copies of one fare filing, for one watch."""
    fw = fare_world(n)
    w = night_watch(n)
    fw.list = [w]
    a = Actor(fw, design)
    trig = Triggers(a.store.rs if isinstance(a.store, Persisted)
                    else Persisted().rs, "fare-watch")
    wakes = [(144 + k, 0.0) for k in range(6)]
    wakes += [(144 + k // 6, 5 + 10 * (k % 6) + 0.5) for k in range(35)]
    wakes.sort()
    h = Hour(144)
    runs = reports = 0
    for hr, minute in wakes:
        now = at(hr, minute)
        fw.clock.set(now)
        f, cabin = fare(w, hr)
        dg = offer_digest({"flight_id": w.flight, "fare_usd": f"{f:.2f}",
                           "cabin": cabin})
        if dedupe and not trig.wake((w.wid, hr, dg), now):
            continue
        runs += 1
        before = h.model_calls
        a.check(w, hr, h, f"{w.wid}@{hr}:{minute:g}")
        reports += h.model_calls > before or not dedupe
    st = a.store.load(w.wid, w.booked)
    return {"watch": w, "wakes": len(wakes), "runs": runs,
            "model_calls": h.model_calls, "reports": reports,
            "stalls": h.stalls, "status": st["status"],
            "usd": h.spend, "fw": fw}


def inject(kind: str, w: Watch, n_wakes: int = 12) -> int:
    """One injected stall; returns the work steps before the stop,
    or 0 if it never stopped."""
    fw = fare_world(1)
    fw.list = [w]
    fw.book = {w.booking: w}
    fw.offers.book = fw.book
    if kind == "repeat":
        d = replace(V110, version="inj-repeat", persist_verdicts=False)
        offers = [(round(w.booked * 0.9, 2), "basic")] * n_wakes
    else:
        d = replace(V110, version="inj-swing", verdict_slots=1)
        a_, b_ = round(w.booked * 0.9, 2), round(w.booked * 0.88, 2)
        offers = [(a_, "basic"), (b_, "basic")] * (n_wakes // 2)
    calls = iter(offers)

    def handle(tool, args, srv=fw.offers):
        srv.requests += 1
        f, cabin = next(calls)
        return {"offers": [{"flight_id": w.flight,
                            "fare_usd": f"{f:.2f}", "cabin": cabin}]}
    fw.offers.handle = handle
    a = Actor(fw, d)
    h = Hour(200)
    for k in range(n_wakes):
        fw.clock.set(at(200, 4 * k))
        a.check(w, 200, h, f"{w.wid}@inj{k}")
        if h.stalls:
            return h.model_calls
    return 0


def injections(per_kind: int = 20, n: int = WATCHES) -> dict:
    ws = fare_world(n).list
    out = {}
    for kind in ("repeat", "swing"):
        steps = [inject(kind, ws[37 * i]) for i in range(per_kind)]
        out[kind] = steps
    return out


def replay(days: int = 17, n: int = WATCHES, loop_day: float | None
           = None, first_day: int = 0, store_kind: str = "run_store",
           restart_every: int = 0, verify: bool = True) -> dict:
    """June 12 onward under 1.1.0, every call through the enforcer
    with the loop-day scope; the waiver watch joins on June 25."""
    spec = dict(FARE_WATCH)
    if loop_day is not None:
        spec["budget"] = dict(spec["budget"], loop_day_usd=loop_day)
    enf = LoopEnforcer.for_specs(spec, WAIVER_WATCH)
    fw = fare_world(n)
    grant(fw)
    control = Control(fw)
    store = Persisted() if store_kind == "run_store" else Memory()
    a = Actor(fw, V110, store=store, enforcer=enf, control=control)
    v = Verifier(fw)
    per_day: dict[str, dict] = {}
    hours = []
    notices = list(NOTICES)
    for hr in range(24 * first_day, 24 * (first_day + days)):
        if restart_every and hr % restart_every == 0 and \
                isinstance(store, Memory):
            store.restart()
        h = a.run_hour(hr)
        r = v.check_hour(hr, h, store) if verify else {"green": True}
        for x in h.handoffs:
            v.handed_off(next(w for w in fw.list if w.wid == x[0]),
                         store.load(x[0], 0)["floor_usd"])
        d = per_day.setdefault(day_of(hr), {
            "runs": 0, "calls": 0, "usd": 0.0, "vouchers": 0,
            "voucher_usd": 0.0, "handoffs": 0, "stops": 0,
            "green": 0, "hours": 0, "stalls": 0, "waiver_usd": 0.0,
            "first_stop": None})
        d["runs"] += h.claimed
        d["calls"] += h.model_calls
        d["usd"] += h.spend
        d["vouchers"] += len(h.vouchers)
        d["voucher_usd"] += sum(x[1] for x in h.vouchers)
        d["handoffs"] += len(h.handoffs)
        d["stops"] += len(h.budget_stops)
        if h.budget_stops and d["first_stop"] is None:
            d["first_stop"] = hr
        d["stalls"] += len(h.stalls)
        d["green"] += r["green"]
        d["hours"] += 1
        hours.append((hr, h, r))
        end = at(hr + 1)
        while notices and notices[0][1] < end.isoformat():
            nid, when, k = notices.pop(0)
            res = run_notice(fw, enf, control, nid, when, k)
            per_day[day_of(hr)]["waiver_usd"] += res["usd"]
    return {"days": per_day, "hours": hours, "enf": enf, "fw": fw,
            "control": control, "store": store,
            "runs_over": enf.runs_over({"fare-watch": spec["budget"][
                "run_usd"], "waiver-watch": WAIVER_WATCH["budget"][
                "run_usd"]})}
