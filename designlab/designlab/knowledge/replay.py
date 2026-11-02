"""Eleven days of metric queries through the guard (Chapter 20 lab).

The supervisor console went live on the layer on Thursday, May 21, 2026.
This replays a synthetic mix of 1,436 metric queries for May 21 to 31
from 39 callers: 30 team leads (ops, one to three desks each), six
finance analysts, and three risk analysts. The mix is invented and
seeded; the guard, layer, and estimator are the ones the chapter uses.

Owen Fletcher's review is the `audit` function: for every answered
query it reads the tables and columns the compiled SQL touched and
checks them against the caller's entitlement again, independently of
the step that let the query run, and checks the desk filter on
desk-scoped metrics.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from common.rand import seeded

from . import entitle as E
from . import layer as L
from . import sql as S

START, END = date(2026, 5, 21), date(2026, 5, 31)
N_QUERIES = 1436


def callers() -> list[E.Entitlement]:
    r = seeded(20, "replay-callers")
    from .warehouse import DESKS
    out = []
    for i in range(30):
        desks = r.sample(DESKS, r.randint(1, 3))
        out.append(E.from_token(E.issue(f"lead{i + 1:02d}", ["ops"], desks,
                                        f"sess-lead{i + 1:02d}")))
    for i in range(6):
        out.append(E.from_token(E.issue(f"fin{i + 1}", ["finance"], [],
                                        f"sess-fin{i + 1}")))
    for i in range(3):
        out.append(E.from_token(E.issue(f"risk{i + 1}", ["risk"], [],
                                        f"sess-risk{i + 1}")))
    return out


EVENTS = ("status_polls", "itinerary_views")


def _query(r, layer: L.Layer, ent: E.Entitlement, day: date
           ) -> L.MetricQuery:
    names = list(layer.metrics)
    role = ent.roles[0]
    if role == "ops" and r.random() < 0.17:
        name = r.choice(EVENTS)
    elif role == "ops" and r.random() < 0.05:
        name = r.choice(["change_cost_usd", "refunds_amount_usd",
                         "model_spend_usd", "refund_avg_usd"])
    else:
        mine = [n for n in names if n not in EVENTS and
                layer.metrics[n].entitle and
                (ent.has_any(layer.metrics[n].entitle) or
                 r.random() < 0.03)]
        name = r.choice(mine)
    m = layer.metrics[name]
    if name in EVENTS:
        span = r.choice([7, 7, 14, 14, 21, 28, 30, 31, 31, 45, 60])
    else:
        span = r.choice([1, 7, 7, 14, 30, 30, 31, 90, 120, 365])
    end = day - timedelta(days=r.choice([0, 1, 1, 1, 2, 7]))
    start = end - timedelta(days=span - 1)
    pick = [d for d in m.dims if not layer.dimensions[d] or
            r.random() < 0.15]
    dims = tuple(r.sample(pick, min(len(pick), r.choice([0, 0, 1, 1, 2]))))
    grain = r.choice(["none", "day", "week", "month"] if span > 7
                     else ["none", "day"])
    filters = ()
    if "change_type" in m.dims and r.random() < 0.12:
        v = r.choice(L.VALUES["change_type"] + ("involuntary", "refund"))
        filters = (("change_type", v),)
    return L.MetricQuery(name, start, end, dims, grain, filters)


@dataclass
class Replay:
    rows: list          # (day, caller, query, decision)
    by_reason: Counter
    estimated: int      # compiled queries that had an estimate
    audit_findings: list


def run(seed: int = 20, guard: S.Guard | None = None) -> Replay:
    g = guard or S.Guard(seed=seed)
    people = callers()
    r = seeded(seed, "replay")
    days = [START + timedelta(days=i) for i in range((END - START).days + 1)]
    weights = [1.0 if d.weekday() < 5 else 0.35 for d in days]
    rows = []
    for _ in range(N_QUERIES):
        day = r.choices(days, weights)[0]
        ent = r.choice(people)
        q = _query(r, g.layer, ent, day)
        rows.append((day, ent, q, g.ask(q, ent)))
    reasons = Counter(d.reason or "answered" for *_, d in rows)
    est = sum(1 for *_, d in rows if d.sql and d.estimate is not None)
    return Replay(rows, reasons, est, audit(g, rows))


def audit(g: S.Guard, rows: list) -> list[str]:
    """Owen's review: re-derive every answered query's reads."""
    out = []
    for day, ent, q, d in rows:
        if d.status != "answered":
            continue
        reads, _ = S.reads_of(g.scratch, d.sql)
        for why in E.check_reads(reads, ent):
            out.append(f"{ent.subject} {q.metric}: {why}")
        m = g.layer.metrics[q.metric]
        if m.desk_scoped and ent.desks and "desk IN" not in d.sql:
            out.append(f"{ent.subject} {q.metric}: no desk filter")
    return out


def compiled_count(rep: Replay) -> int:
    return sum(1 for *_, d in rep.rows if d.sql)
