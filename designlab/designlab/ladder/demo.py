"""Chapter 46 demo: the ladder, the clock, the rubric, and calibration.

    python3 -m ladder.demo                         # every part
    python3 -m ladder.demo --part levels
    python3 -m ladder.demo --part clock
    python3 -m ladder.demo --part worked
    python3 -m ladder.demo --part drill --answer A03b
    python3 -m ladder.demo --part score --answer A08a
    python3 -m ladder.demo --part score --answer A08a --fault no-estimate
    python3 -m ladder.demo --part v0
    python3 -m ladder.demo --part agree
    python3 -m ladder.demo --part model
    python3 -m ladder.demo --part tiers
    python3 -m ladder.demo --part card

Offline. The model and drill parts replay recorded fixtures. Lakeshore
figures are illustrative.
"""
from __future__ import annotations

import argparse
import sys

from common.text import emit

from . import agree, clock, notes, rubric, scores
from .levels import LEVELS, TIER_TOP, tier_for
from .prompts import PROMPTS, by_level
from .rubric import CRITERIA, SHORT

PARTS = ("levels", "clock", "worked", "drill", "score", "v0", "agree",
         "model", "tiers", "card")
FAULTS = ("no-estimate", "model-first")
STRONG = [f"A{i:02d}a" for i in range(1, 13)]
WEAK = [f"A{i:02d}b" for i in range(1, 13)]


def part_levels() -> None:
    emit("== the ladder: seven levels, twelve prompts ==")
    emit("lvl  name                                 bar  gap  prompts")
    bl = by_level()
    for lv in LEVELS:
        emit(f"{lv.code}   {lv.name:<36} {lv.bar:>3}  {lv.lead_gap}"
             f"   {' '.join(bl[lv.code])}")
    emit(f"levels {len(LEVELS)}, prompts {len(PROMPTS)}, "
         f"rubric 1 ({len(CRITERIA)} criteria, 0 to 2 each)")


def part_clock() -> None:
    emit("== the clock: four marks over Chapter 5's eight slices ==")
    for m, task, _ in clock.MARKS:
        emit(f"by {m:>2} min  {task}")
        for s in clock.slices(m):
            emit(f"           {s}")


def _row(s: rubric.Score) -> str:
    cells = " ".join(f"{s.cells[c]:>3}" for c in CRITERIA)
    return (f"{s.aid}  {s.level} {cells}  {s.total:>3}  "
            f"{len(clock.closed(notes.load(s.aid)))}/5  "
            f"{'clears' if s.cleared else 'below'}")


def _head() -> str:
    return ("ans   lvl " + " ".join(SHORT[c] for c in CRITERIA)
            + "  tot  gaps  verdict")


def part_worked() -> None:
    emit("== twelve worked answers, scored by the rubric ==")
    emit(_head())
    total_gaps = 0
    for aid in STRONG:
        s = rubric.score(notes.load(aid))
        total_gaps += len(clock.closed(notes.load(aid)))
        emit(_row(s))
    emit(f"worked 12, levels 7, gaps closed {total_gaps} of 60")


def part_drill(aid: str) -> None:
    from .drill import run
    p = PROMPTS[notes.load(aid)["answer"]["prompt"]]
    emit(f"== drill: {aid}, {p['id']} ({p['level']}) {p['title']} ==")
    note = notes.load(aid)
    emit(f"minutes on the model: {notes.minutes_on(note, 'model')}"
         f" of 45")
    import textwrap
    for r in run(note):
        emit(f"{r['minute']:>2} min  {'met ' if r['ok'] else 'MISS'}"
             f"  {r['task']}: {r['board']}")
        if r["question"]:
            if r["first_problems"]:
                emit("        first reply: "
                     + "; ".join(r["first_problems"]))
            for ln in textwrap.wrap(f"ask {r['gap']} ({r['source']}): "
                                    f"{r['question']}", 60):
                emit("        " + ln)


def part_score(aid: str, fault: str | None) -> int:
    note = notes.load(aid)
    if fault == "no-estimate":
        note = notes.without(note, "estimate")
    elif fault == "model-first":
        note = notes.load("A03b")
    s = rubric.score(note)
    tag = f", fault {fault}" if fault else ""
    emit(f"== score {aid}{tag} ==")
    for c in CRITERIA:
        emit(f"  {c:<14} {s.cells[c]}")
    lv = [x for x in LEVELS if x.code == s.level][0]
    emit(f"  total {s.total} of 14, bar {lv.bar} for {s.level}")
    for _, task, ok, board in clock.check(note):
        if not ok:
            emit(f"  missed mark: {task} ({board})")
    if s.cleared:
        emit(f"  clears {s.level}")
        return 0
    emit(f"  below {s.level}:")
    for r in s.reasons:
        emit(f"    {r}")
    return 1


def part_v0() -> None:
    emit("== component list (v0) against the rubric (v1) ==")
    emit("ans    v0 boxes  v1 total  v1 verdict")
    rows = []
    for aid in STRONG + WEAK:
        n = notes.load(aid)
        s = rubric.score(n)
        rows.append((rubric.score_v0(n), aid, s))
    rows.sort(key=lambda r: (-r[0], r[1]))
    for v0, aid, s in rows[:6]:
        emit(f"{aid}  {v0:>8}  {s.total:>8}  "
             f"{'clears' if s.cleared else 'below'} {s.level}")
    emit(f"... {len(rows) - 6} more")
    best0 = rows[0]
    best1 = max(rows, key=lambda r: (r[2].total, r[1]))
    emit(f"v0 ranks first: {best0[1]} ({best0[0]} boxes), "
         f"below {best0[2].level}")
    emit(f"v1 ranks first: {best1[1]} ({best1[2].total} of 14)")


def _pct(p: tuple[int, int]) -> str:
    return f"{p[0]:>3}/{p[1]:<3} {p[0] / p[1]:.2f}"


def part_agree() -> None:
    d, h = scores.scorer("daniel"), scores.scorer("hannah")
    before, after = scores.split()
    emit("== calibration: Daniel Price and Dr. Hannah Clarke ==")
    emit("24 answers, 7 criteria, scored blind from the note")
    allp = agree.cells(d, h)
    emit(f"all cells    {_pct(agree.exact(allp))}  "
         f"kappa {agree.kappa(allp):.2f}")
    emit("criterion       before (16)    after (8)")
    for i, c in enumerate(CRITERIA):
        b = agree.exact(agree.cells(d, h, before, i))
        a = agree.exact(agree.cells(d, h, after, i))
        emit(f"{c:<14}  {_pct(b)}  {_pct(a)}")
    b = agree.exact(agree.cells(d, h, before))
    a = agree.exact(agree.cells(d, h, after))
    emit(f"{'all':<14}  {_pct(b)}  {_pct(a)}")
    emit("calibrated Monday, October 19, 2026")


def part_model() -> None:
    from .live import replay
    rows, info = replay()
    d, h = scores.scorer("daniel"), scores.scorer("hannah")
    chk = {a: rubric.score(n).row() for a, n in notes.load_all().items()}
    ids = sorted(rows)
    emit(f"== scorers against the people ({len(ids)} answers) ==")
    emit(f"model {info['model']}, replayed from fixtures")
    if info["bad"]:
        emit(f"unparsed: {', '.join(info['bad'])} (key missing)")
    emit("pair                    exact          kappa")
    for name, x in (("checker", chk), ("model", rows)):
        for who, y in (("Daniel", d), ("Hannah", h)):
            p = agree.cells(x, y, ids)
            emit(f"{name:<8} vs {who:<10}  {_pct(agree.exact(p))}"
                 f"  {agree.kappa(p):.2f}")
    p = agree.cells(d, h, ids)
    emit(f"{'Daniel':<8} vs {'Hannah':<10}  {_pct(agree.exact(p))}"
         f"  {agree.kappa(p):.2f}")
    emit("criterion       model vs Daniel")
    for i, c in enumerate(CRITERIA):
        emit(f"{c:<14}  {_pct(agree.exact(agree.cells(rows, d, ids, i)))}")
    emit(f"tokens in {info['in']:,}, out {info['out']:,}")


def part_tiers() -> None:
    emit("== tiers onto the ladder ==")
    for t, top in TIER_TOP.items():
        emit(f"{t:<10} clears L1 to {top}")
    for cleared in (["L1", "L2", "L3"], ["L1", "L2", "L3", "L4", "L5"],
                    ["L1", "L3", "L4", "L5", "L6", "L7"]):
        emit(f"cleared {' '.join(cleared):<21} -> {tier_for(cleared)}")


def part_card() -> None:
    gaps = sum(len(clock.closed(notes.load(a))) for a in STRONG)
    clears = sum(rubric.score(notes.load(a)).cleared for a in STRONG)
    weak = sum(rubric.score(notes.load(a)).cleared for a in WEAK)
    d, h = scores.scorer("daniel"), scores.scorer("hannah")
    p = agree.exact(agree.cells(d, h))
    emit("== ladder card, November 2, 2026 ==")
    emit(f"worked interviews    {len(STRONG)}")
    emit(f"levels               {len(LEVELS)}")
    emit("rubric               1 (7 criteria, 14 points)")
    emit(f"gaps closed          {gaps} of 60")
    emit(f"worked that clear    {clears} of 12")
    emit(f"other answers clear  {weak} of 12")
    emit(f"two-scorer agreement {p[0] / p[1]:.2f} ({p[0]} of {p[1]})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--answer", default=None)
    ap.add_argument("--fault", choices=FAULTS)
    a = ap.parse_args(argv)
    parts = [a.part] if a.part else list(PARTS)
    rc = 0
    for i, part in enumerate(parts):
        if i:
            emit()
        if part == "levels":
            part_levels()
        elif part == "clock":
            part_clock()
        elif part == "worked":
            part_worked()
        elif part == "drill":
            part_drill(a.answer or "A03b")
        elif part == "score":
            rc = part_score(a.answer or "A08a", a.fault)
        elif part == "v0":
            part_v0()
        elif part == "agree":
            part_agree()
        elif part == "model":
            part_model()
        elif part == "tiers":
            part_tiers()
        elif part == "card":
            part_card()
    return rc


if __name__ == "__main__":
    sys.exit(main())
