"""Chapter 47 lab: the interview bank, its index, and the loop.

    python3 -m bank.demo47 [--part NAME] [--snapshot]

Parts: source, rounds, card, short, notes, loop, fault, appendix,
filter, sixty, parts. With no --part, every part runs in that order.
"""
from __future__ import annotations

import argparse
import re
from collections import Counter

from common.text import emit
from . import appendix, loop, sides
from .manuscript import (ROOT, SNAPSHOT, available, chapter_files,
                         load_snapshot)
from .schema import BankError
from .taxonomy import LOOP_FORMATS, ROUNDS, TIER_LEVEL, TYPES

PARTS = ("source", "rounds", "card", "short", "notes", "loop", "fault",
         "appendix", "filter", "sixty", "parts")


def _rows(snap: bool) -> tuple[list[dict], str]:
    if snap or not available(ROOT):
        return appendix.load(use_snapshot=True), "snapshot"
    return appendix.rows(ROOT), "manuscript"


def part_source(rs, src):
    emit(f"source: {src}")
    if src == "manuscript":
        emit(f"chapter files read: {len(chapter_files(ROOT))}")
    emit(f"questions parsed and valid: {len(rs)}")
    emit(f"with a weak line: {sum(1 for r in rs if r['weak_line'])}")


def part_rounds(rs, src):
    declared = Counter(r["round"] for r in rs)
    emit("declared round tags in the manuscript")
    for tag, n in declared.most_common():
        emit(f"  {tag:24} {n:4}")
    emit("routed to a round tag (bank.rounds)")
    routed = Counter(r["loop_round"] for r in rs)
    for tag in ROUNDS:
        mark = "format" if tag in LOOP_FORMATS else "outside"
        emit(f"  {tag:24} {routed.get(tag, 0):4}  {mark}")
    rules = Counter(r["rule"] for r in rs)
    emit("by routing rule")
    for rule, n in rules.most_common():
        emit(f"  {rule:32} {n:4}")


def part_card(rs, src):
    c = appendix.card(rs)
    emit("interview bank card")
    emit(f"  chapters            {c['chapters']:4} of {appendix.CHAPTERS}")
    emit(f"  round tags          {c['tags']:4} (formats {c['formats']} of 7)")
    emit(f"  questions indexed   {c['questions']:4} (floor "
         f"{appendix.TARGET}; first plan {appendix.PROMPT_TARGET})")
    emit(f"  hiring side         {c['hiring_side']:4}")
    lv = c["levels"]
    emit("  levels              " + ", ".join(
        f"{t} {lv.get(t, 0)}" for t in TIER_LEVEL))
    ty = c["types"]
    emit("  types               " + ", ".join(
        f"{letter} {ty.get(k, 0)}" for k, letter in TYPES.items()))
    emit(f"  target met          {'yes' if c['target_met'] else 'no'}")


def part_short(rs, src):
    c = appendix.card(rs)
    short = c["hiring_short"]
    emit(f"hiring-side minimum: {appendix.HIRING_MIN} per chapter")
    emit(f"  chapters meeting it   {c['chapters'] - len(short)} "
         f"of {c['chapters']}")
    emit("  short: " + (", ".join(f"ch{n}" for n in short) or "none"))


def part_notes(rs, src):
    data, heard = sides.read()
    listen = data["listen"]
    emit(f"control round, {data['round']['date']}, "
         f"{data['round']['interviewer']}")
    for h in heard:
        emit(f"{h.candidate}: heard {len(h.first)} of {len(listen)}")
        for item in listen:
            at = h.first.get(item)
            emit(f"  {item:11} " + (f"minute {at}" if at is not None
                                     else "never"))
        for at, text in h.circled:
            emit(f"  circled at {at}: {text}")
        emit("  policy engine named: "
             + ("yes" if h.named_policy else "NO"))


def part_loop(rs, src):
    cfg = loop.config()
    for role in cfg["roles"].values():
        planned = loop.plan(rs, role["rounds"], role["tier"],
                            seed=role["id"], rounds=cfg["rounds"])
        mins = loop.total(planned)
        emit(f"{role['title']} ({role['tier']}, x{role['openings']})")
        for p in planned:
            r = p.round
            ev = "rec" if r.evidence == "recommended" else "pub"
            emit(f"  {r.tag:22} {r.minutes:3}m {ev} pool {p.pool:3} "
                 + " ".join(p.questions))
        screen = planned[0].round.minutes
        emit(f"  final loop {mins - screen} minutes "
             f"({(mins - screen) / 60:.2f} hours), "
             f"{len(planned) - 1} rounds")


def part_fault(rs, src):
    path = ROOT / "ch47.md"
    if not path.exists():
        emit("fault: needs the manuscript; skipped on the snapshot")
        return
    text = path.read_text(encoding="utf-8")
    broken = re.sub(r"\*\*Q47\.3 ", "**", text, count=1)
    emit("fault: Q47.3 loses its ID, so it has no chapter")
    try:
        appendix.rows(ROOT, extra={47: broken})
    except BankError as exc:
        for p in exc.problems:
            emit(f"  FAIL {p}")
        emit("  appendix not written")
        return
    emit("  generator accepted it (this is a bug)")


def part_appendix(rs, src):
    md = appendix.render(rs)
    lines = md.splitlines()
    heads = [ln for ln in lines if ln.startswith("### ")]
    emit(f"Appendix J: {len(lines)} lines, {len(md.split())} words")
    emit(f"  chapter rows {sum(1 for ln in lines if ln[:2] == '| ' and ln[2:3].isdigit())}"
         f", round sections {len(heads)}, levels "
         f"{sum(1 for ln in lines if ln.startswith('- ') and 'clears' in ln)}"
         f", Parts {sum(1 for ln in lines if ln.startswith('- Part'))}")
    entries = sum(1 for ln in lines if re.match(r"- Q\d+\.\d+ ", ln))
    emit(f"  question entries {entries}, each pointing to a chapter")
    snap = load_snapshot(SNAPSHOT) if SNAPSHOT.exists() else []
    same = [(r["qid"], r["loop_round"]) for r in snap] == [
        (r["qid"], r["loop_round"]) for r in rs]
    emit(f"  snapshot {SNAPSHOT.name}: {len(snap)} rows, "
         f"{'matches' if same else 'differs from'} this run")


def part_filter(rs, src):
    hits = [r for r in rs if r["loop_round"] == "control-plane-security"
            and r["level"] == "staff"]
    emit(f"control-plane-security at staff (L6): {len(hits)}")
    by_ch = Counter(r["chapter"] for r in hits)
    items = [f"ch{c} {n}" for c, n in sorted(by_ch.items())]
    for i in range(0, len(items), 8):
        emit("  " + ", ".join(items[i:i + 8]))


def part_sixty(rs, src):
    tags = ["system-design", "control-plane-security"]
    planned = loop.fit(rs, 60, "staff", tags, seed="sixty")
    emit("a 60-minute loop, staff, two rounds")
    for p in planned:
        emit(f"  {p.round.tag:22} {p.round.minutes:3}m pool {p.pool:3} "
             + " ".join(p.questions))


def part_parts(rs, src):
    emit("hiring-side questions per Part")
    for n, chs, name in appendix.PARTS:
        qs = [r for r in rs if r["chapter"] in chs]
        hs = sum(1 for r in qs if r["hiring_side"])
        emit(f"  Part {n} {name:30} {hs:3} of {len(qs):3}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="bank.demo47")
    ap.add_argument("--part", choices=PARTS)
    ap.add_argument("--snapshot", action="store_true")
    a = ap.parse_args(argv)
    rs, src = _rows(a.snapshot)
    for name in ([a.part] if a.part else PARTS):
        emit(f"== {name} ==")
        globals()[f"part_{name}"](rs, src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
