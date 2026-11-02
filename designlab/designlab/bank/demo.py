"""Load the sample bank, index it, and fail a question with no chapter.

    python3 -m bank.demo
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from common.text import emit
from .index import group, reconcile
from .loader import load, parse_table
from .schema import validate
from .taxonomy import ROUNDS, TYPES

FIXTURES = Path(__file__).with_name("fixtures")


def main() -> None:
    qs = load(FIXTURES / "sample-bank.md")
    chapter = load(FIXTURES / "sample-chapter.md")
    emit(f"bank: {len(qs)} questions; chapter markup: {len(chapter)}")
    emit("\nBy round")
    by_round = group(qs, "round")
    for key in ROUNDS:
        ids = ", ".join(q.qid for q in by_round.get(key, []))
        emit(f"  {key:23} {ids or '-'}")
    emit("\nBy type")
    counts = Counter(q.type for q in qs)
    for key, letter in TYPES.items():
        emit(f"  {letter} {key:12} {counts[key]}")
    emit("\nChapter markup checked against the bank")
    for problem in reconcile(chapter, qs) or ["all present, tags agree"]:
        emit(f"  {problem}")
    emit("\nA row with no chapter, an unknown round and a repeated ID")
    bad = parse_table(
        "| ID | Chapter | Type | Round | Level | Question |\n"
        "|---|---|---|---|---|---|\n"
        "| Q9.1 | | C | lunch | L4 | Why? |\n"
        "| Q9.1 | 9 | C | phone-screen | L4 | Why again? |\n", "bad.md")
    for problem in validate(bad):
        emit(f"  FAIL {problem}")


if __name__ == "__main__":
    main()
