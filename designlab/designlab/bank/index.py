"""Build the interview index (the v0 generator behind Appendix J).

    python3 -m bank.index FILE [FILE ...]

Prints Markdown: questions by round, then by type, each pointing to its
chapter. Answers are never repeated. Fails if any question fails the
schema, including a question with no chapter.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

from .loader import load
from .schema import BankError, Question, validate
from .taxonomy import ROUNDS, TYPES


def group(questions: list[Question], attr: str) -> dict[str, list]:
    out = defaultdict(list)
    for q in questions:
        out[getattr(q, attr)].append(q)
    for qs in out.values():
        qs.sort(key=lambda q: (q.chapter or 0, q.qid))
    return dict(out)


def reconcile(chapter: list[Question], bank: list[Question]) -> list[str]:
    """Every chapter question must be in the bank with the same tags."""
    rows = {q.qid: q for q in bank}
    out = []
    for q in chapter:
        b = rows.get(q.qid)
        if b is None:
            out.append(f"{q.qid}: in the chapter, missing from the bank")
            continue
        for attr in ("chapter", "type", "round", "level"):
            if getattr(q, attr) != getattr(b, attr):
                out.append(f"{q.qid}: {attr} {getattr(q, attr)!r} in "
                           f"chapter, {getattr(b, attr)!r} in bank")
    return out


def render(questions: list[Question]) -> str:
    problems = validate(questions)
    if problems:
        raise BankError(problems)
    lines = ["# Interview question index", "",
             f"{len(questions)} questions from "
             f"{len({q.chapter for q in questions})} chapters.", "",
             "## By round", ""]
    by_round = group(questions, "round")
    for key in ROUNDS:
        if key in by_round:
            lines += [f"### {ROUNDS[key]}", ""]
            lines += [f"- {q.qid} ({q.type_letter}, {q.level}): "
                      f"Chapter {q.chapter}" for q in by_round[key]]
            lines.append("")
    lines += ["## By type", ""]
    by_type = group(questions, "type")
    for key, letter in TYPES.items():
        if key in by_type:
            ids = ", ".join(q.qid for q in by_type[key])
            lines += [f"- {letter} {key}: {ids}"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    qs = []
    try:
        for name in argv:
            qs += load(Path(name), check=False)
        sys.stdout.write(render(qs))
    except BankError as exc:
        for p in exc.problems:
            print(f"FAIL {p}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
