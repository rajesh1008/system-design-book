"""Chapter 9 demos. Offline: no API, no network.

    python3 -m durable.demo incident   the March 10 restart, both ways
    python3 -m durable.demo kill       the kill suite, three strategies
    python3 -m durable.demo inject     a checkpoint without the permission
    python3 -m durable.demo replay     strict, other model, other code
    python3 -m durable.demo wait       seven simulated days for a partner
    python3 -m durable.demo bench      replay time on 2,000 runs
    python3 -m durable.demo card       the durability card
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from .bench import bench
from .killsuite import OPTIONS, lab_spec, rate, run_to_end, suite
from .models import FixtureA, FixtureB, Sampled
from .replay import replay
from .store import RunStore
from .workflow import (DURATION, STEPS, Crash, Engine, Kill, SimClock,
                       Spec, propose_v1)
from .world import World, pay_key

CRASH = "2026-03-10T14:05:00-05:00"
RESTART = "2026-03-10T14:09:00-05:00"
REPORT = "2026-03-10T14:19:00-05:00"
REBOOK_AT = {"read_request": 11, "model_plan": 17, "fetch_fares": 12,
             "model_choose": 2, "propose": 23, "verify": 16, "close": 12}
REFUND_AT = {"read_request": 6, "model_plan": 9, "fetch_fares": 7,
             "propose": 5, "wait_approval": 9, "verify": 6, "close": 5}
FILED = ["13:22", "13:31", "13:38", "13:44", "13:49", "13:53", "13:58",
         "14:01", "14:04"]
GRANTED = {"13:44": "14:06", "13:53": "14:07", "14:01": "14:08"}


def t(hhmm: str) -> datetime:
    return datetime.fromisoformat(f"2026-03-10T{hhmm}:00-05:00")


def incident_runs():
    """140 runs and where each was at 2:05 p.m. CT."""
    runs, n = [], 0
    for kind, table in (("rebook", REBOOK_AT), ("refund", REFUND_AT)):
        for pos, count in table.items():
            for _ in range(count):
                n += 1
                runs.append((f"RUN-{n:04d}", kind, pos))
    return runs


def kill_for(pos: str):
    i = STEPS.index(pos)
    if pos == "model_choose":
        return Kill("model_choose", "work")          # mid-call
    if pos == "wait_approval":
        return Kill(at=datetime.fromisoformat(CRASH))
    if i == 0:
        return Kill("read_request", "work")
    return Kill(STEPS[i - 1], "commit")


def before_filing() -> float:
    return sum(DURATION[s] for s in STEPS[:6])


def incident(strategy: str, base: Path, model) -> dict:
    waits = iter(FILED)
    for run_id, kind, pos in incident_runs():
        n = int(run_id[4:])
        spec = Spec(run_id, f"LTG-{4472000 + n}", kind, 486.0, OPTIONS,
                    480.0, regrant=False)
        start = t("14:04")
        if kind == "refund" and pos in ("verify", "close"):
            start, spec.grant_after_s = t("13:40"), 240.0
        if pos == "wait_approval":
            filed = next(waits)
            start = t(filed) - timedelta(seconds=before_filing())
            g = GRANTED.get(filed)
            spec.grant_after_s = None if g is None else \
                (t(g) - t(filed)).total_seconds()
        clock = SimClock(start.isoformat())
        eng = Engine(base, strategy, model, clock, kill_for(pos))
        eng.submit(spec)
        try:
            eng.run(run_id, horizon=t("14:19"))
        except Crash:
            pass
        eng.close()
        clock.t = datetime.fromisoformat(RESTART)       # the restart
        eng = Engine(base, strategy, model, clock, Kill())
        ctx = eng.run(run_id, horizon=datetime.fromisoformat(REPORT))
        eng.close()
    waiting = [r for r, k, p in incident_runs() if p == "wait_approval"]
    return measure(base, waiting)


def measure(base: Path, waiting: list[str]) -> dict:
    c = sqlite3.connect(base / "lab.db")
    World(c).answer(datetime.fromisoformat(REPORT))  # the desk's own clock
    q = ",".join("?" * len(waiting))
    reqs = c.execute(f"select count(*) from desk where run_id in ({q})",
                     waiting).fetchone()[0]
    paid = {r[0] for r in c.execute("select pay_key from processor")}
    granted = c.execute(f"select permission_id from desk where run_id in "
                        f"({q}) and status='granted'", waiting).fetchall()
    orphan = sum(pay_key(p, "refund") not in paid for (p,) in granted)
    offers = c.execute("select run_id, count(distinct kind), count(*) "
                       "from notices where kind like 'offer:%' "
                       "group by run_id").fetchall()
    timers = c.execute("select count(distinct run_id) from timers "
                       "where run_id in (" + q + ")", waiting).fetchone()[0]
    esc = c.execute("select count(*) from timers where state='fired' "
                    "and name='escalate' and run_id in (" + q + ")",
                    waiting).fetchone()[0]
    tickets = c.execute("select itinerary, count(*) from airline group "
                        "by itinerary having count(*) > 1").fetchall()
    credits = c.execute("select itinerary, count(*) from processor group "
                        "by itinerary having count(*) > 1").fetchall()
    out = {"waiting": len(waiting), "requests": reqs,
           "orphaned": orphan, "timers": timers, "escalated": esc,
           "two_offers": sum(1 for _, d, _n in offers if d > 1),
           "offers_sent_twice": sum(1 for _, _d, k in offers if k > 1),
           "dup_tickets": len(tickets), "dup_credits": len(credits),
           "open": c.execute(f"select count(*) from desk where run_id in "
                             f"({q}) and status='open'",
                             waiting).fetchone()[0]}
    c.close()
    return out


def cmd_incident():
    print("Tuesday March 10, 2026; restart 2:05 p.m. CT, back 2:09 p.m.")
    print("140 runs in flight: 93 rebook-only, 47 with a refund;")
    print("9 waiting on a supervisor. Counts read at 2:19 p.m. CT.")
    rows = {}
    for strategy in ("framework", "durable"):
        with tempfile.TemporaryDirectory() as d:
            rows[strategy] = incident(strategy, Path(d), Sampled(0.55))
    labels = [("requests", "requests for the 9 waiting runs"),
              ("orphaned", "grants no run picked up"),
              ("timers", "waiting runs with a stored timer"),
              ("escalated", "escalations fired by 2:19"),
              ("open", "requests still open at 2:19"),
              ("two_offers", "customers shown two flights"),
              ("offers_sent_twice", "offers sent twice"),
              ("dup_tickets", "itineraries rebooked twice"),
              ("dup_credits", "itineraries refunded twice")]
    print(f"{'':38}{'framework':>11}{'durable':>9}")
    for k, label in labels:
        print(f"{label:38}{rows['framework'][k]:>11}"
              f"{rows['durable'][k]:>9}")


def cmd_kill():
    print("kill suite: refund run, 12 steps x 2 kill points = 24")
    print(f"{'step':20}{'memory':>8}{'framework':>11}{'durable':>9}")
    res = {s: suite(s) for s in ("memory", "framework", "durable")}
    for i, step in enumerate(STEPS):
        cells = []
        for s in ("memory", "framework", "durable"):
            pair = res[s][2 * i: 2 * i + 2]
            cells.append(f"{sum(r['correct'] for r in pair)}/2")
        print(f"{i + 1:>2} {step:17}{cells[0]:>8}{cells[1]:>11}"
              f"{cells[2]:>9}")
    tot = [f"{rate(res[s]):.0%}" for s in ("memory", "framework",
                                           "durable")]
    print(f"{'resume rate':20}{tot[0]:>8}{tot[1]:>11}{tot[2]:>9}")
    f = [r for r in res["framework"] if not r["correct"]]
    worst = max(f, key=lambda r: r["requests"] + r["tickets"] +
                r["credits"])
    print(f"framework worst: kill at {worst['step']}/{worst['phase']}: "
          f"{worst['requests']} requests,")
    print(f"  {worst['tickets']} tickets, {worst['credits']} credits "
          f"for one itinerary")
    return res


def cmd_inject():
    print("injection: checkpoint rewritten without the pending fields")
    for variant in ("journal kept", "journal lost too"):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            spec = lab_spec()
            eng, ctx, _ = run_to_end(base, "durable", spec,
                                     Kill("wait_approval", "commit"),
                                     restarts=0)
            eng.close()
            c = sqlite3.connect(base / "lab.db")
            RunStore(c).strip_pending(spec.run_id)
            if variant == "journal lost too":
                c.execute("delete from journal where run_id=? and seq<=7",
                          (spec.run_id,))
                c.execute("update desk set req_key=null")
                c.commit()
            c.close()
            eng = Engine(base, "durable", FixtureA(),
                         SimClock("2026-03-10T13:50:00-05:00"))
            ctx = eng.run(spec.run_id)
            w = eng.world
            print(f"-- {variant}")
            for e in ctx.events:
                print("   " + e[:64])
            print(f"   status {ctx.status}; requests "
                  f"{w.count('select count(*) from desk')}, tickets "
                  f"{len(w.tickets(spec.itinerary))}, credits "
                  f"{w.credits(spec.itinerary)}")
            eng.close()


def cmd_replay():
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        spec = lab_spec()
        eng, ctx, _ = run_to_end(base, "durable", spec, Kill())
        eng.close()
        c = sqlite3.connect(base / "lab.db")
        print("strict replay (journal only, nothing called):")
        print("  " + replay(c, spec.run_id).line())
        print("replay with fixture-b in place of fixture-a:")
        print("  " + replay(c, spec.run_id, model=FixtureB()).line())

        def propose_v2(s, choice):          # a change under review
            body = propose_v1(s, choice)
            body["refund_usd"] = max(0.0, body["refund_usd"] - 25.0)
            return body
        print("replay with proposal code that nets a $25 fee:")
        print("  " + replay(c, spec.run_id, propose=propose_v2).line())
        c.close()
    print("re-running the run instead of replaying it (sampled model):")
    model = Sampled(1.0)
    with tempfile.TemporaryDirectory() as d:
        spec = lab_spec()
        eng, ctx, _ = run_to_end(Path(d), "durable", spec, Kill(),
                                 model=model)
        first = ctx.out["model_choose"]["flight"]
        eng.close()
    with tempfile.TemporaryDirectory() as d:
        eng, ctx, _ = run_to_end(Path(d), "durable", spec, Kill(),
                                 model=model)
        print(f"  first run chose {first}; the re-run chose "
              f"{ctx.out['model_choose']['flight']}")
        eng.close()


def wait_week(strategy: str, answer: bool = True) -> dict:
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        start = "2026-03-16T09:00:00-05:00"
        grant = 6 * 86400 + 6 * 3600 + 10 * 60      # day 6, 3:10 p.m.
        spec = Spec("RUN-0907", "LTG-4471902", "waiver", 486.0, OPTIONS,
                    grant if answer else None, regrant=False,
                    poll_s=300.0,
                    timers=[("remind-24h", 86400), ("remind-72h", 259200),
                            ("escalate", 5 * 86400),
                            ("deadline", 7 * 86400)])
        clock, model = SimClock(start), FixtureA()
        end = clock.now() + timedelta(days=8)
        crashes, ctx = 0, None
        while clock.now() < end:
            kill = Kill(at=clock.now() + timedelta(hours=6))
            eng = Engine(base, strategy, model, clock, kill)
            eng.submit(spec)
            try:
                ctx = eng.run(spec.run_id, horizon=end)
                eng.close()
                if ctx.status in ("done", "held for a person"):
                    break
            except Crash:
                crashes += 1
                eng.close()
        c = sqlite3.connect(base / "lab.db")
        fired = c.execute("select name from timers where state='fired' "
                          "order by fire_at").fetchall()
        out = {"crashes": crashes,
               "requests": c.execute("select count(*) from desk"
                                     ).fetchone()[0],
               "fired": [f for (f,) in fired],
               "status": ctx.status if ctx else "none",
               "decision": (ctx.out.get("wait_approval") or {}).get(
                   "decision") if ctx else None,
               "ended": clock.now()}
        c.close()
    return out


def cmd_wait():
    print("a partner waiver, filed Monday March 16, 9:00 a.m. CT;")
    print("the process is killed every 6 hours for 8 days")
    for strategy in ("memory", "framework", "durable"):
        o = wait_week(strategy)
        print(f"{strategy:10} crashes {o['crashes']:>2}, requests "
              f"{o['requests']:>2}, status {o['status']}")
        if o["fired"]:
            print(f"{'':10} timers fired: {', '.join(o['fired'])}")
        if o["decision"]:
            print(f"{'':10} decision {o['decision']} at "
                  f"{o['ended']:%a %b %d %H:%M} CT")
    o = wait_week("durable", answer=False)
    print(f"durable, no answer: {', '.join(o['fired'])}")
    print(f"{'':10} decision {o['decision']} at "
          f"{o['ended']:%a %b %d %H:%M} CT")


def cmd_bench():
    b = bench(2000)
    print(f"replay benchmark: {b['runs']} runs, {b['steps']} journaled "
          f"steps")
    print(f"  p50 {b['p50_ms']:.2f} ms  p99 {b['p99_ms']:.2f} ms  "
          f"max {b['max_ms']:.2f} ms  diverged {b['diverged']}")
    return b


def cmd_card():
    res = suite("durable")
    b = bench(2000)
    with tempfile.TemporaryDirectory() as d:
        inc = incident("durable", Path(d), Sampled(0.55))
    print("durability card, lab run")
    print(f"  resume rate (kill suite)     {rate(res):>6.0%}   "
          f"target 100%")
    print(f"  replay p99 (2,000 runs)      {b['p99_ms']:>6.2f} ms"
          f" target < 3 s")
    print(f"  waits outstanding at 2:19    {inc['open']:>6}   "
          f"each with a timer")


def main(argv):
    cmds = {"incident": cmd_incident, "kill": cmd_kill,
            "inject": cmd_inject, "replay": cmd_replay, "wait": cmd_wait,
            "bench": cmd_bench, "card": cmd_card}
    for a in argv or list(cmds):
        cmds[a]()
        print()


if __name__ == "__main__":
    main(sys.argv[1:])
