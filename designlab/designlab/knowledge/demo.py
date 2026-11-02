"""Chapter 20 lab: the knowledge plane for the supervisor console.

    python3 -m knowledge.demo                       # everything, seed 20
    python3 -m knowledge.demo --part guard          # one part
    python3 -m knowledge.demo --inject no-estimate  # estimator down
    python3 -m knowledge.demo --part layer --add-metric   # Try It
    python3 -m knowledge.demo --part guard --no-row-limit # Try It
    python3 -m knowledge.demo --part entitle --as-user talvarez

The live part replays the twelve recorded small-model translations from
knowledge/fixtures; `python3 -m knowledge.live` records them. No other
part calls a model. The warehouse is a seeded SQLite sample with
production-sized statistics; amounts are illustrative.
"""
from __future__ import annotations

import argparse
import re
import statistics
import sys
from collections import Counter
from datetime import date

from common.text import emit

from . import entitle as E
from . import graph as G
from . import layer as L
from . import live as LV
from . import replay as R
from . import sql as S
from .questions import CALLERS

PARTS = ("opening", "layer", "guard", "entitle", "graph", "live",
         "replay", "card")
YEAR_SCAN = ("SELECT COUNT(*) FROM refunds r JOIN booking_events e "
             "ON json_extract(e.payload, '$.refund_id') = r.refund_id "
             "WHERE e.payload LIKE '%refund%' "
             "AND e.event_at >= date('now', '-1 year')")
EXTRA = {"name": "refunds_agent", "label": "Refunds handled by the agent",
         "table": "refunds", "kind": "count",
         "where": "handled_by = 'agent'", "dims": ["change_type", "carrier"],
         "entitle": ["ops", "finance", "risk"], "max_window_days": 400,
         "owner": "Customer Operations (Marcus Bell)"}


def teresa() -> E.Entitlement:
    return E.from_token(CALLERS["talvarez"])


def _tb(b: float) -> str:
    if b >= 1e12:
        return f"{b / 1e12:,.1f} TB"
    return f"{b / 1e9:,.0f} GB" if b >= 1e9 else f"{b / 1e6:,.0f} MB"


def _usd(x: float) -> str:
    return f"${x:,.2f}" if x >= 0.995 else f"${x:.4f}"


def _secs(x: float) -> str:
    return f"{x / 60:,.0f} min" if x >= 120 else f"{x:.1f} s"


def show(d: S.Decision, label: str) -> None:
    e = d.estimate
    est = "no estimate" if e is None else \
        f"est {_tb(e.bytes)}, {_usd(e.usd)}, {_secs(e.seconds)}"
    out = d.status if d.status == "answered" else f"refused: {d.reason}"
    emit(f"  {label}")
    emit(f"    {est}")
    emit(f"    {out}" + (f" ({d.detail})" if d.detail else ""))


def part_opening(guard: S.Guard) -> None:
    emit("the shadow trial's query, Wednesday, May 6, 2026, 8:52 a.m.")
    emit("  team lead: 'how many refunds last year'")
    raw = S.Guard(guard.layer, raw_allowed=True, estimator=guard.estimator)
    d = raw.ask_sql(YEAR_SCAN, teresa())
    show(d, "raw SQL, as the model wrote it (re-estimated in the lab)")
    if d.estimate:
        e = d.estimate
        emit(f"    months scanned: " + ", ".join(
            f"{t} {n}" for t, n in sorted(e.tables.items())))
        emit(f"    actual bytes {_tb(e.actual_bytes)} "
             f"(${e.actual_usd:,.2f}); estimate off by "
             f"{100 * (e.bytes / e.actual_bytes - 1):+.0f}%")
    for (a, b), what in [(((2025, 1, 1), (2025, 12, 31)), "calendar 2025"),
                         (((2025, 5, 27), (2026, 5, 26)),
                          "trailing twelve months")]:
        q = L.MetricQuery("refunds_count", date(*a), date(*b))
        d = guard.ask(q, teresa())
        v = d.rows[0][1] if d.rows else None
        show(d, f"layer: refunds_count, {what}")
        emit(f"    value {v:,}" if v is not None else "    no value")


def part_layer(extra: bool) -> L.Layer:
    lay = L.load(extra=[EXTRA] if extra else None)
    tables = Counter(m.table for m in lay.metrics.values())
    kinds = Counter(m.kind for m in lay.metrics.values())
    gated = sum(1 for m in lay.metrics.values()
                if set(m.entitle) <= {"finance", "risk"})
    emit(f"knowledge.layer v{lay.version}: {len(lay.metrics)} metrics, "
         f"{len(lay.dimensions)} dimensions, k = {lay.k_min_rows}")
    for i, chunk in enumerate(_wrap("by table: " + ", ".join(
            f"{t} {n}" for t, n in sorted(tables.items())), 62)):
        emit(("  " if i == 0 else "    ") + chunk)
    emit("  by kind: " + ", ".join(f"{k} {n}" for k, n in
                                    sorted(kinds.items())))
    emit(f"  finance- or risk-only: {gated}; desk-scoped: "
         f"{sum(m.desk_scoped for m in lay.metrics.values())}")
    q = L.MetricQuery("refund_clock_met_rate", date(2026, 5, 1),
                      date(2026, 5, 26), ("desk",), "none")
    c = L.compile_query(lay, q, ("CHI-2", "CHI-3"))
    emit("  refund_clock_met_rate by desk, May 1-26, desks CHI-2, CHI-3:")
    text = re.sub(r" (FROM|WHERE|GROUP BY|ORDER BY) ", r"\n\1 ", c.sql)
    text = re.sub(r" AND (?!\?)", "\n  AND ", text)
    for line in text.split("\n"):
        while len(line) > 64:
            cut = line.rfind(" ", 0, 64)
            emit("    " + line[:cut])
            line = "  " + line[cut + 1:]
        emit("    " + line)
    if extra:
        from .translate import CONTRACT
        enum = set(CONTRACT.output["metric"]["enum"])
        emit(f"  added {EXTRA['name']}: layer has it; contract enum "
             f"{'has' if EXTRA['name'] in enum else 'does not have'} it")
        g = S.Guard(lay)
        d = g.ask(L.MetricQuery("refunds_agent", date(2026, 5, 1),
                                date(2026, 5, 26)), teresa())
        show(d, "refunds_agent, May 1-26")
        if d.rows:
            emit(f"    value {d.rows[0][1]:,}")
    return lay


def part_guard(guard: S.Guard, no_row_limit: bool) -> int:
    ent = teresa()
    emit("knowledge.sql guard: restrict, estimate, limits, entitlement, "
         "run")
    cases = [
        ("refunds_count, 2025", L.MetricQuery(
            "refunds_count", date(2025, 1, 1), date(2025, 12, 31))),
        ("refund_margin_usd (no such metric)", L.MetricQuery(
            "refund_margin_usd", date(2026, 4, 1), date(2026, 4, 30))),
        ("status_polls by day, Jan 1-May 26", L.MetricQuery(
            "status_polls", date(2026, 1, 1), date(2026, 5, 26), (), "day")),
        ("status_polls by carrier, Apr 27-May 26", L.MetricQuery(
            "status_polls", date(2026, 4, 27), date(2026, 5, 26),
            ("carrier",), "day")),
        ("status_polls by carrier, May 1-26", L.MetricQuery(
            "status_polls", date(2026, 5, 1), date(2026, 5, 26),
            ("carrier",), "day")),
        ("refunds_amount_usd by carrier, Q1", L.MetricQuery(
            "refunds_amount_usd", date(2026, 1, 1), date(2026, 3, 31),
            ("carrier",))),
    ]
    bad = 0
    for label, q in cases:
        d = guard.ask(q, ent)
        show(d, label)
        bad += d.reason == "unestimated"
    d = guard.ask_sql("DELETE FROM refunds WHERE issued_at >= "
                      "'2026-05-26'", ent)
    show(d, "DELETE FROM refunds ... (raw)")
    emit("  row limit:")
    for lim in ((1000, 0) if no_row_limit else (1000,)):
        g = S.Guard(guard.layer, row_limit=lim, estimator=guard.estimator)
        q = L.MetricQuery("changes_count", date(2025, 1, 1),
                          date(2025, 12, 31), ("desk", "carrier"), "day")
        d = g.ask(q, ent)
        e = d.estimate
        emit(f"    limit {lim or 'none'}: est ${e.usd:.4f} "
             f"({_tb(e.bytes)}); rows {len(d.rows):,}; "
             f"truncated {d.truncated}" if e else
             f"    limit {lim or 'none'}: refused: {d.reason}")
    emit("  trail line, last decision:")
    for chunk in _wrap(d.trail_line, 64):
        emit("    " + chunk)
    return bad


def _wrap(s: str, n: int) -> list[str]:
    out = []
    while len(s) > n:
        cut = s.rfind(" ", 0, n)
        cut = n if cut < 0 else cut
        out.append(s[:cut])
        s = s[cut:].lstrip()
    return out + [s]


def part_entitle(guard: S.Guard, as_user: str | None) -> None:
    emit("knowledge.entitle: the question carries the caller's grant")
    q = L.MetricQuery("refunds_amount_usd", date(2026, 1, 1),
                      date(2026, 3, 31), ("carrier",))
    who = [as_user] if as_user else ["pnatarajan", "talvarez"]
    for u in who:
        ent = E.from_token(CALLERS[u])
        d = guard.ask(q, ent)
        show(d, f"{u} ({', '.join(ent.roles)}): refunds_amount_usd by "
                f"carrier, Q1 2026")
        if d.rows:
            top = max(d.rows, key=lambda r: r[2] or 0)
            emit(f"    {len(d.rows)} rows; largest {top[1]} "
                 f"${top[2]:,.0f}")
    ent = teresa()
    q = L.MetricQuery("approval_wait_p95_minutes", date(2026, 5, 1),
                      date(2026, 5, 26), ("desk",))
    d = guard.ask(q, ent)
    show(d, "talvarez: approval_wait_p95_minutes by desk, May 1-26")
    emit("    rows: " + "; ".join(f"{r[1]} {r[2]} min" for r in d.rows))
    tok = CALLERS["talvarez"]
    forged = tok[:-6] + ("AAAAAA" if not tok.endswith("AAAAAA") else "BBBBBB")
    try:
        E.from_token(forged)
        emit("  forged token: accepted (this is a bug)")
    except E.BadToken as e:
        emit(f"  forged token: refused ({e})")
    q = L.MetricQuery("refunds_count", date(2026, 3, 1), date(2026, 3, 31),
                      ("customer_id",))
    d = guard.ask(q, ent)
    show(d, "talvarez: refunds_count by customer_id, March")
    risk = E.from_token(E.issue("rmorgan-team", ["risk"], [], "sess-risk"))
    d = guard.ask(q, risk)
    emit(f"  risk analyst, same query: {d.status}; {len(d.rows)} rows")
    emit(f"    {d.suppressed} below k = {guard.layer.k_min_rows} rows "
         "suppressed")


def part_graph() -> None:
    g = G.lakeshore_sample()
    emit(f"knowledge.graph: {len(g.kind)} nodes, {g.edges()} edges")
    for actor, it in [("Ngozi Okafor", "LTG-5208841"),
                      ("Ngozi Okafor", "LTG-5208842"),
                      ("Corporate arranger", "LTG-5208842"),
                      ("Party friend", "LTG-5300000")]:
        ok, why = G.may_act(g, actor, it)
        emit(f"  may {actor} change {it}? {'yes' if ok else 'no'}")
        for i, chunk in enumerate(_wrap(why.replace(" / ", ", "), 62)):
            emit("    " + chunk)
    follow = [("on_flight", "in"), ("has_segment", "in")]
    for cap, budget, steps in [(200, 4, follow), (50, 4, follow),
                               (200, 4, follow * 3)]:
        w = G.traverse(g, "FLT-904417", steps, "itinerary", budget, cap)
        emit(f"  itineraries on FLT-904417, cap {cap}, budget {budget}, "
             f"{len(steps)} steps:")
        emit(f"    {len(w.found)} found, " + ("complete" if w.complete
             else f"incomplete: {w.stopped_by}"))


def part_live(guard: S.Guard) -> None:
    emit("twelve questions, recorded, layer path and raw-SQL path")
    emit("id  layer metric             layer        raw SQL     raw $")
    lines, rows = LV.run(replay=True)
    for ln in lines:
        emit(ln)
    for r in rows:
        t, d = r["translation"], r["layer_decision"]
        if t.status == "clarify" or r["layer"] == "not_in_layer":
            emit(f"  {r['id']} {t.status if t.status != 'ok' else 'ok'}"
                 + (f", guard: {d.detail}" if d else ""))
            if t.assumption:
                for chunk in _wrap(f"model: {t.assumption}", 62):
                    emit("      " + chunk)


def part_replay(rep: R.Replay) -> None:
    n = len(rep.rows)
    emit(f"replay: May 21-31, 2026, {n:,} metric queries, 39 callers")
    for k in ("answered", "entitlement", "cost", "window", "not_in_layer",
              "unestimated"):
        v = rep.by_reason.get(k, 0)
        emit(f"  {k:<13}{v:>6,}  {100 * v / n:5.1f}%")
    comp = R.compiled_count(rep)
    emit(f"  compiled {comp:,}; estimated before running "
         f"{rep.estimated:,}")
    ratios = [d.estimate.bytes / d.estimate.actual_bytes
              for *_, d in rep.rows if d.status == "answered"
              and d.estimate.bytes > 1.1e7]
    if ratios:
        qs = statistics.quantiles(ratios, n=20)
        emit(f"  estimate / actual bytes, {len(ratios)} answered over "
             "10 MB:")
        emit(f"    median {statistics.median(ratios):.2f}, "
             f"p5 {qs[0]:.2f}, p95 {qs[-1]:.2f}")
    near = [d for *_, d in rep.rows if d.reason == "cost"]
    if near:
        lo = min(d.estimate.usd for d in near)
        hi = max(d.estimate.usd for d in near)
        emit(f"  cost refusals: estimates ${lo:.2f} to ${hi:.2f}")
    emit(f"  audit (Owen's review): {len(rep.audit_findings)} answered "
         f"queries outside entitlement")
    for f in rep.audit_findings[:3]:
        emit(f"    {f}")


def part_card(lay: L.Layer, rep: R.Replay) -> None:
    n = len(rep.rows)
    comp = R.compiled_count(rep)
    est = rep.estimated
    cost = rep.by_reason.get("cost", 0)
    emit("knowledge card, as of May 31, 2026")
    emit(f"  metrics in the layer        {len(lay.metrics)}")
    emit(f"  queries estimated first     {100 * est / comp:.0f}%")
    emit(f"  refused on cost             {100 * cost / n:.0f}% "
         f"({cost} of {n:,})")
    emit(f"  outside entitlement         {len(rep.audit_findings)}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="knowledge.demo")
    ap.add_argument("--seed", type=int, default=20)
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--inject", choices=["no-estimate"])
    ap.add_argument("--add-metric", action="store_true")
    ap.add_argument("--no-row-limit", action="store_true")
    ap.add_argument("--as-user", choices=sorted(CALLERS))
    a = ap.parse_args(argv)
    est = (lambda reads, months: None) if a.inject else S.estimate
    lay = L.load(extra=[EXTRA] if a.add_metric else None)
    guard = S.Guard(lay, seed=a.seed, estimator=est)
    parts = [a.part] if a.part else list(PARTS)
    bad = 0
    rep = None
    for p in parts:
        if p == "opening":
            part_opening(guard)
        elif p == "layer":
            part_layer(a.add_metric)
        elif p == "guard":
            bad += part_guard(guard, a.no_row_limit)
        elif p == "entitle":
            part_entitle(guard, a.as_user)
        elif p == "graph":
            part_graph()
        elif p == "live":
            part_live(guard)
        elif p in ("replay", "card"):
            rep = rep or R.run(a.seed, guard)
            (part_replay if p == "replay" else
             lambda r: part_card(lay, r))(rep)
        emit("")
    if a.inject:
        emit(f"injected: estimator returns nothing; {bad} queries refused "
             "as unestimated, none ran")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
