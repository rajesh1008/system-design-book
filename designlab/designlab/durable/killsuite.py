"""The kill suite: one refund run, killed once at each of 24 points
(12 steps, before and after each commit), then restarted.

A run passes when it resumes from its stored position and ends with
one approval request, one ticket, one credit, and one offer sent to
the customer. The suite reports the share of kill points that pass.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .models import FixtureA
from .workflow import STEPS, Crash, Engine, Kill, SimClock, Spec

START = "2026-03-10T13:30:00-05:00"
OPTIONS = [{"flight": "LK 2210", "dep": "17:05", "fare": 412.0},
           {"flight": "LK 2286", "dep": "19:40", "fare": 368.0}]


def lab_spec(run_id="RUN-0901", kind="refund", grant_after_s=360.0,
             **kw) -> Spec:
    return Spec(run_id, "LTG-4471902", kind, 486.0, OPTIONS,
                grant_after_s, **kw)


def run_to_end(base: Path, strategy: str, spec: Spec, kill: Kill,
               model=None, clock=None, horizon=None, restarts=3):
    """Run, and after each crash start a new Engine on the same files."""
    model = model or FixtureA()
    clock = clock or SimClock(START)
    crashes, ctx, eng = 0, None, None
    for _ in range(restarts + 1):
        eng = Engine(base, strategy, model, clock, kill)
        eng.submit(spec)
        try:
            ctx = eng.run(spec.run_id, horizon)
            break
        except Crash:
            crashes += 1
            eng.close()       # uncommitted writes roll back here
            clock.advance(240)
    return eng, ctx, crashes


def outcome(eng: Engine, spec: Spec, ctx) -> dict:
    w = eng.world
    offers = {k for (k,) in w.c.execute(
        "select kind from notices where run_id=? and kind like 'offer:%'",
        (spec.run_id,))}
    sent = w.count("select count(*) from notices where run_id=? and "
                   "kind like 'offer:%'", spec.run_id)
    o = {"resumed": ctx.resumed_from is not None and ctx.resumed_from > 0,
         "done": ctx.status == "done",
         "requests": w.count("select count(*) from desk where run_id=?",
                             spec.run_id),
         "tickets": len(w.tickets(spec.itinerary)),
         "credits": w.credits(spec.itinerary),
         "offers": sent, "distinct": len(offers)}
    o["correct"] = (o["done"] and o["requests"] == 1 and
                    o["tickets"] == 1 and o["credits"] == 1 and
                    o["offers"] == 1)
    return o


def suite(strategy: str, model_factory=FixtureA) -> list[dict]:
    rows = []
    for step in STEPS:
        for phase in ("work", "commit"):
            with tempfile.TemporaryDirectory() as d:
                spec = lab_spec()
                eng, ctx, crashes = run_to_end(Path(d), strategy, spec,
                                               Kill(step, phase),
                                               model_factory())
                o = outcome(eng, spec, ctx)
                eng.close()
            o.update(step=step, phase=phase, crashes=crashes)
            rows.append(o)
    return rows


def rate(rows) -> float:
    return sum(r["correct"] for r in rows) / len(rows)
