"""The Appendix J generator over the whole manuscript (Chapter 47).

    python3 -m bank.appendix [--root DIR] [--snapshot] [--write FILE]

Reads every chapter's interview section (bank.manuscript), validates
every question, routes each to a round tag (bank.rounds), and renders
the index: by chapter, by round tag, by level, and by Part (the
book's competency axis), each entry pointing to its chapter, with no
answer repeated. It fails, and writes nothing, if any question fails
the schema, including a question with no chapter.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from .manuscript import ROOT, SNAPSHOT, load_snapshot, scan, snapshot
from .rounds import hiring_side, route
from .schema import BankError
from .taxonomy import LOOP_FORMATS, ROUNDS, TIER_LEVEL, TYPES

PARTS = (
    (1, range(1, 7), "Systems that act"),
    (2, range(7, 13), "Distributed foundations"),
    (3, range(13, 19), "Models and inference"),
    (4, range(19, 25), "Knowledge, retrieval, memory"),
    (5, range(25, 31), "Runtime, harness, loops"),
    (6, range(31, 37), "Control, security, evaluation"),
    (7, range(37, 43), "Operations, cost, platform"),
    (8, range(43, 49), "Worked designs, interviews"),
)
TARGET = 702           # the Blueprint's floor (Chapter 47 resolution)
PROMPT_TARGET = 290    # the book prompt's figure, revised
CHAPTERS = 48
HIRING_MIN = 2         # hiring-side questions per chapter


def part_of(chapter: int) -> int:
    for n, chs, _ in PARTS:
        if chapter in chs:
            return n
    raise ValueError(f"chapter {chapter} is in no Part")


def rows(root: Path = ROOT, extra: dict[int, str] | None = None
         ) -> list[dict]:
    """One dict per question, validated; raises BankError."""
    s = scan(root, extra)
    problems = s.problems(answers=True)
    if problems:
        raise BankError(problems)
    out = []
    for q in s.questions:
        r = route(q)
        out.append({
            "qid": q.qid, "chapter": q.chapter, "type": q.type,
            "round": q.round, "level": q.level, "loop_round": r.tag,
            "rule": r.rule, "hiring_side": int(hiring_side(q)),
            "answer_words": q.answer_words,
            "weak_line": int(q.weak_line), "text": q.text})
    return out


def load(root: Path = ROOT, use_snapshot: bool = False) -> list[dict]:
    from .manuscript import available
    if use_snapshot or not available(root):
        return load_snapshot(SNAPSHOT)
    return rows(root)


def card(rs: list[dict]) -> dict:
    chapters = sorted({r["chapter"] for r in rs})
    tags = Counter(r["loop_round"] for r in rs)
    per_ch = Counter(r["chapter"] for r in rs if r["hiring_side"])
    short = [c for c in chapters if per_ch.get(c, 0) < HIRING_MIN]
    return {
        "chapters": len(chapters), "questions": len(rs),
        "tags": len([t for t in ROUNDS if tags.get(t)]),
        "formats": len([t for t in LOOP_FORMATS if tags.get(t)]),
        "by_tag": tags, "hiring_side": sum(per_ch.values()),
        "hiring_short": short,
        "levels": Counter(r["level"] for r in rs),
        "types": Counter(r["type"] for r in rs),
        "declared": Counter(r["round"] for r in rs),
        "target_met": len(rs) >= TARGET and len(chapters) == CHAPTERS,
    }


def render(rs: list[dict]) -> str:
    """Appendix J in Markdown. Headings only; never an answer."""
    c = card(rs)
    by_ch = Counter(r["chapter"] for r in rs)
    hs = Counter(r["chapter"] for r in rs if r["hiring_side"])
    lines = ["# Appendix J. The interview bank, indexed", "",
             f"{c['questions']} questions from {c['chapters']} "
             f"chapters, under {c['tags']} round tags. Each entry "
             "points to the chapter that answers it.", "",
             "## By chapter", "",
             "| Chapter | Part | Questions | Hiring side |",
             "|---:|---:|---:|---:|"]
    for ch in sorted(by_ch):
        lines.append(f"| {ch} | {part_of(ch)} | {by_ch[ch]} | "
                     f"{hs.get(ch, 0)} |")
    lines += ["", "## By round tag", ""]
    for tag in ROUNDS:
        qs = [r for r in rs if r["loop_round"] == tag]
        if not qs:
            continue
        lines += [f"### {ROUNDS[tag]} ({len(qs)})", ""]
        for r in sorted(qs, key=_order):
            text = f" {r['text']}" if r.get("text") else ""
            lines.append(f"- {r['qid']} ({TYPES[r['type']]}, "
                         f"{r['level']}):{text} Chapter {r['chapter']}.")
        lines.append("")
    lines += ["## By level", ""]
    for tier in TIER_LEVEL:
        ids = [r["qid"] for r in sorted(rs, key=_order)
               if r["level"] == tier]
        lines.append(f"- {tier} (clears {TIER_LEVEL[tier]}): "
                     f"{len(ids)} questions: {', '.join(ids)}")
    lines += ["", "## By Part", ""]
    for n, chs, name in PARTS:
        ids = [r["qid"] for r in sorted(rs, key=_order)
               if r["chapter"] in chs]
        lines.append(f"- Part {n}, {name}: {len(ids)} questions, "
                     f"{ids[0]} to {ids[-1]}" if ids else
                     f"- Part {n}, {name}: none")
    return "\n".join(lines) + "\n"


def _order(r: dict) -> tuple:
    ch, n = r["qid"][1:].split(".")
    return (int(ch), int(n))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="bank.appendix")
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--snapshot", action="store_true",
                    help="read the committed index, not the manuscript")
    ap.add_argument("--write", type=Path, help="write Appendix J here")
    ap.add_argument("--save-snapshot", action="store_true")
    a = ap.parse_args(argv)
    try:
        rs = load(a.root, a.snapshot)
    except BankError as exc:
        for p in exc.problems:
            print(f"FAIL {p}", file=sys.stderr)
        print("appendix not written", file=sys.stderr)
        return 1
    if a.save_snapshot:
        snapshot(rs)
    md = render(rs)
    if a.write:
        a.write.write_text(md, encoding="utf-8")
    else:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
