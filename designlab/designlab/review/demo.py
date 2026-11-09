"""Chapter 42 demo: the review, the record, the store, the card.

    python3 -m review.demo                       # every part
    python3 -m review.demo --part gaps [--design points-transfer-v1]
    python3 -m review.demo --part checklist [--design ...]
    python3 -m review.demo --part verdict [--design ...]
    python3 -m review.demo --part verdict --inject self-verify
    python3 -m review.demo --part verdict --inject no-kill-switch
    python3 -m review.demo --part verdict --inject no-stop
    python3 -m review.demo --part verdict --design points-transfer-v2 \
        --conditions
    python3 -m review.demo --part record [--minutes]
    python3 -m review.demo --part store [--as-of 2026-09-08]
    python3 -m review.demo --part log
    python3 -m review.demo --part card

Offline and deterministic. No model call and no key.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import argparse
from datetime import date

from common.text import emit

from . import board, checklist, gaps
from .log import OUTCOMES, by_month, card, load_log
from .record import MINUTES, validate
from .store import load_store
from .submission import apply_conditions, inject, load

PARTS = ("gaps", "checklist", "verdict", "record", "store", "log",
         "card")
V1, V2 = "points-transfer-v1", "points-transfer-v2"


def show_gaps(sub) -> None:
    emit(f"== five gap questions: {sub.name} ==")
    emit("chain: " + " > ".join(gaps.CHAIN[:3]) + " >")
    emit("       " + " > ".join(gaps.CHAIN[3:]))
    n = 0
    for gid, q, ok, probs in gaps.walk(sub):
        emit(f"{gid} {'yes' if ok else 'NO':<3} {q}")
        for p in probs:
            emit(f"     {p}")
        n += ok
    emit(f"{n} of 5 answered")


def show_checklist(sub) -> None:
    emit(f"== checklist by plane: {sub.name} ==")
    res = checklist.run(sub)
    for r in res:
        flag = ("shape" if r.item.shape else
                "block" if r.item.blocking else "")
        emit(f"{r.item.id} {'PASS' if r.passed else 'FAIL'} "
             f"{flag:<5} {r.item.question}")
        for p in r.problems:
            emit(f"   {p}")
    n = sum(r.passed for r in res)
    emit(f"{n} of {len(res)} pass")


def show_verdict(sub) -> None:
    v = board.decide(sub)
    emit(f"== verdict: {v.design} ==")
    emit(f"checklist      {v.passed} of {v.total}")
    emit(f"shape fails    {', '.join(v.shape) or 'none'}")
    emit(f"blocking fails {', '.join(v.blocking) or 'none'}")
    emit(f"other fails    {', '.join(v.other) or 'none'}")
    emit(f"outcome        {v.outcome.upper()}")
    emit(f"may go live    {'yes' if v.may_ship else 'no'}")


def show_record(minutes: bool) -> None:
    store = load_store()
    recs = ([MINUTES] if minutes else []) + [store.get("DR-42.1")]
    for i, r in enumerate(recs):
        if i:
            emit()
        probs = validate(r)
        emit(f"== record {r.id} ==")
        emit(f"decision: {r.decision}")
        for p in probs:
            emit(f"  {p}")
        emit(f"{len(probs)} problems: "
             f"{'REFUSED' if probs else 'ACCEPTED'}")


def show_store(as_of: date) -> None:
    store = load_store()
    emit(f"== record store as of {as_of.isoformat()} ==")
    emit(f"records {len(store.all())}; invalid {len(store.invalid())}")
    emit(f"revisited {len(store.revisited())}:")
    for r in store.revisited():
        emit(f"  {r.id:<8} {r.revisited_on}  {r.revisited_by}")
    due = store.due(as_of)
    emit(f"past revisit date, not revisited {len(due)}:")
    for r in due:
        emit(f"  {r.id:<8} due {r.revisit_date}  {r.title}")


def show_log() -> None:
    log = load_log()
    emit("== review log by month ==")
    emit(f"{'month':<8} {'approve':>7} {'change':>7} {'decline':>7}")
    for m, c in sorted(by_month(log).items()):
        emit(f"{m:<8} " + " ".join(f"{c[o]:>7}" for o in OUTCOMES))
    emit(f"{'total':<8} " + " ".join(
        f"{sum(e.outcome == o for e in log):>7}" for o in OUTCOMES))


def show_card() -> None:
    emit("== review card, 2026-09-08 (Owen Fletcher) ==")
    for k, v in card(load_log()).items():
        emit(f"{k:<32} {v}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="review.demo")
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--design")
    ap.add_argument("--inject",
                    choices=("self-verify", "no-kill-switch", "no-stop"))
    ap.add_argument("--minutes", action="store_true")
    ap.add_argument("--conditions", action="store_true")
    ap.add_argument("--as-of", default="2026-09-08")
    a = ap.parse_args(argv)
    parts = [a.part] if a.part else list(PARTS)
    for i, part in enumerate(parts):
        if i:
            emit()
        default = V2 if a.inject else V1
        sub = load(a.design or default)
        if a.inject:
            sub = inject(sub, a.inject)
        if a.conditions:
            for c in sub.conditions:
                emit(f"condition {c['item']}: owner {c['owner']}")
            sub = apply_conditions(sub)
        if part == "gaps":
            show_gaps(sub)
        elif part == "checklist":
            show_checklist(sub)
        elif part == "verdict":
            show_verdict(sub)
        elif part == "record":
            show_record(a.minutes or not a.part)
        elif part == "store":
            show_store(date.fromisoformat(a.as_of))
        elif part == "log":
            show_log()
        elif part == "card":
            show_card()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
