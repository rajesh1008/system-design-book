"""Chapter 19 demo. Offline and seeded.

    python3 -m retrieval.demo --case opening    the May 4 question
    python3 -m retrieval.demo --case provenance one hit, as returned
    python3 -m retrieval.demo --case golden     the golden set by method
    python3 -m retrieval.demo --case loop       one agentic loop, traced
    python3 -m retrieval.demo --case loops      forty desk tasks
    python3 -m retrieval.demo --case budgets    grounding by budget
    python3 -m retrieval.demo --case loops --inject no-stop

Flags for the Try It Yourself steps: --budget N, --no-rerank,
--dates pre|post|off, --cite verified|read, --add-superseded.
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter
from datetime import date

from common.text import emit

from . import agentic, grounding, hybrid
from .evaluate import CONFIGS, score
from .golden import questions
from .tasks import RUNAWAY, tasks

OPENING_Q = ("Prairie Airways, Main fare: switch to an earlier flight "
             "on the day I travel. What does it cost?")
ISSUED = date(2026, 5, 2)      # the ticket's issue date: the as-of date


def _row(h, as_of) -> str:
    d = h.doc
    eff = "in effect" if d.in_effect(as_of) else "superseded"
    if d.kind in ("note", "help", "supplier"):
        eff = {"note": "desk note", "help": "help page",
               "supplier": "supplier"}[d.kind]
    return f"{h.rank}  {d.doc_id:20} {eff:10}  {h.why}"[:70]


def opening(args) -> None:
    emit(f"question: {OPENING_Q[:58]}")
    emit(f"  {OPENING_Q[58:]}")
    emit(f"as of: ticket issued {ISSUED.isoformat()}")
    emit()
    emit("pilot (dense only, no date filter, no rerank), top 5")
    for h in hybrid.search(OPENING_Q, ISSUED, k=5, method="dense",
                           dates="off", use_rerank=False):
        emit(_row(h, ISSUED))
    top = hybrid.search(OPENING_Q, ISSUED, k=1, method="dense",
                        dates="off", use_rerank=False)[0].doc
    emit(f"rank 1 says Main: ${top.facts['Main']}, in effect "
         f"{top.effective_from} to {top.effective_to}")
    emit()
    emit(f"hybrid, dates {args.dates}, rerank "
         f"{'off' if args.no_rerank else 'on'}, top 5")
    hits = hybrid.search(OPENING_Q, ISSUED, k=5,
                         use_rerank=not args.no_rerank, dates=args.dates)
    for h in hits:
        emit(_row(h, ISSUED))
    rule = next((h for h in hits if h.doc.kind == "fare-rule"), None)
    if rule is None:
        emit("no fare rule in the top 5")
    else:
        emit(f"first rule at rank {rule.rank} says Main: "
             f"${rule.doc.facts['Main']}, in effect from "
             f"{rule.doc.effective_from}")


def provenance(args) -> None:
    h = hybrid.search(OPENING_Q, ISSUED, k=1)[0]
    for key, val in h.provenance().items():
        emit(f"{key:15} {val}")


def golden(args) -> None:
    qs = questions()
    emit(f"golden set: {len(qs)} questions, recall at 10")
    emit(f"{'configuration':22} {'R@10':>6} {'MRR':>6} {'stale@1':>8} "
         f"{'short':>6}")
    for name, cfg in CONFIGS.items():
        r = score(cfg, qs)
        emit(f"{name:22} {r['recall']:6.1%} {r['mrr']:6.3f} "
             f"{r['stale_at_1']:8d} {r['short']:6d}")
    emit()
    emit("by question style, recall at 10")
    styles = ("code", "ref", "customer", "desk", "notice")
    emit(f"{'configuration':22}" + "".join(f"{s:>9}" for s in styles))
    for name in ("lexical only", "dense only", "hybrid+dates+rerank"):
        cells = []
        for s in styles:
            sub = [q for q in qs if q.style == s]
            cells.append(f"{score(CONFIGS[name], sub)['recall']:9.0%}")
        emit(f"{name:22}" + "".join(cells))


def _kw(args) -> dict:
    return dict(budget=None if args.inject else args.budget,
                use_rerank=not args.no_rerank, dates=args.dates,
                cite=args.cite, inject=args.inject)


def loop(args) -> None:
    task = next(t for t in tasks() if len(t.slots) == 2 and t.answerable
                and len(agentic.run(t).queries) >= 3)
    emit(f"{task.tid} as of {task.as_of}")
    for line in _wrap(task.question):
        emit(f"  {line}")
    r = agentic.run(task, **_kw(args))
    seen: list = []
    for n, q in enumerate(r.queries, 1):
        new = [h for h in r.evidence if h.doc.doc_id in
               {x.doc.doc_id for x in agentic_run_hits(q, task, args)}
               and h.doc.doc_id not in seen]
        seen += [h.doc.doc_id for h in new]
        gaps = agentic.unmet(task, [h for h in r.evidence
                                    if h.doc.doc_id in seen])
        emit(f"q{n}: {q[:64]}")
        emit(f"    unmet after: {', '.join(s.topic for s in gaps) or '-'}")
    emit(f"stop: {r.stop} after {len(r.queries)} queries")
    for slot, doc, verdict in grounding.check(task, r.answer):
        emit(f"  {slot.topic:11} {doc.doc_id if doc else '-':20} "
             f"{verdict}")


def agentic_run_hits(q, task, args):
    return hybrid.search(q, task.as_of, k=agentic.PER_QUERY,
                         use_rerank=not args.no_rerank, dates=args.dates)


def _wrap(text: str, width: int = 66) -> list[str]:
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return out + [line]


def loops(args) -> None:
    ts = tasks()
    kw = _kw(args)
    runs = [agentic.run(t, **kw) for t in ts]
    qn = sorted(len(r.queries) for r in runs)
    emit(f"tasks {len(ts)}, answerable {sum(t.answerable for t in ts)}")
    label = "none" if kw["budget"] is None else kw["budget"]
    emit(f"budget {label}, rerank {'off' if args.no_rerank else 'on'}, "
         f"dates {args.dates}, cite {args.cite}")
    emit(f"queries per task: median {statistics.median(qn):g}, "
         f"p90 {qn[int(0.9 * len(qn)) - 1]}, max {qn[-1]}, "
         f"total {sum(qn)}")
    stops = Counter(r.stop for r in runs)
    emit("stops: " + ", ".join(f"{k} {v}" for k, v in sorted(
        stops.items())))
    emit(f"handed off: {sum(r.handed_off for r in runs)} "
         f"(unanswerable {sum(not t.answerable for t in ts)})")
    g, n = grounding.rate(runs)
    emit(f"claims grounded: {g} of {n} ({g / n:.0%})" if n else
         "claims grounded: none answered")
    bad = Counter(v for r in runs for _, _, v in
                  grounding.check(r.task, r.answer) if v != "grounded")
    for k, v in sorted(bad.items()):
        emit(f"  not grounded, {k}: {v}")
    emit()
    if args.inject:
        run0 = agentic.run(RUNAWAY, inject=args.inject)
        emit(f"{RUNAWAY.tid} (the April 29 question): "
             f"{len(run0.queries)} queries, stop {run0.stop}")
        runs = runs + [run0]
    fails = agentic.check_budget(runs, 8)
    emit(f"budget check (8 per task): "
         f"{'PASS' if not fails else f'FAIL, {len(fails)} tasks over'}")
    for f in fails[:3]:
        emit(f"  {f}")


def budgets(args) -> None:
    ts = tasks()
    emit("grounding by budget, 40 tasks")
    emit(f"{'budget':>6} {'answer anyway':>14} {'hand off':>9} "
         f"{'handed off':>11} {'queries':>8}")
    for b in (1, 2, 3, 4, 6, 8, 12, 20):
        a = [agentic.run(t, budget=b, at_budget="answer") for t in ts]
        h = [agentic.run(t, budget=b) for t in ts]
        ga, na = grounding.rate(a)
        gh, nh = grounding.rate(h)
        emit(f"{b:6d} {ga / na:14.0%} {gh / nh:9.0%} "
             f"{sum(r.handed_off for r in h):11d} "
             f"{sum(len(r.queries) for r in h):8d}")


def add_superseded() -> None:
    """Try It Yourself 3: add an older superseded page, worded like the
    long 2025 page, and see which configurations still rank it."""
    import corpus.docs as D
    from dataclasses import replace
    base = D.documents()
    v1 = D.by_id()["FR-XPA-same-day-v1"]
    old = replace(v1, doc_id="FR-XPA-same-day-v0", version=0,
                  text=v1.text.replace("January 1, 2025",
                                       "January 1, 2024")
                  .replace("$75", "$60"),
                  source=v1.source.replace("/v1", "/v0"),
                  effective_from=date(2024, 1, 1),
                  effective_to=date(2024, 12, 31),
                  superseded_by=v1.doc_id,
                  facts=dict(v1.facts, Main="60"))
    docs = tuple(base) + (old,)
    D.documents = lambda seed=2026: docs              # noqa: E731
    hybrid.documents = D.documents
    hybrid.index.cache_clear()
    emit("added FR-XPA-same-day-v0 (2024, Main $60), worded like v1")


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--case", default="loops",
                   choices=["opening", "provenance", "golden", "loop",
                            "loops", "budgets"])
    p.add_argument("--budget", type=int, default=8)
    p.add_argument("--no-rerank", action="store_true")
    p.add_argument("--dates", default="pre", choices=["pre", "post",
                                                      "off"])
    p.add_argument("--cite", default="verified", choices=["verified",
                                                          "read"])
    p.add_argument("--inject", choices=["no-stop"])
    p.add_argument("--add-superseded", action="store_true")
    args = p.parse_args(argv)
    if args.add_superseded:
        add_superseded()
    {"opening": opening, "provenance": provenance, "golden": golden,
     "loop": loop, "loops": loops, "budgets": budgets}[args.case](args)


if __name__ == "__main__":
    main()
