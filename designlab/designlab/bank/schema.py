"""One interview question, and the checks every question must pass."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .taxonomy import LEVELS, METHODS, ROUNDS, TIERS, TYPES

QID = re.compile(r"^Q(\d{1,2})\.(\d{1,2})$")


@dataclass
class Question:
    qid: str
    chapter: int | None
    type: str
    round: str
    level: str
    text: str
    competency: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    answer_words: int = 0
    weak_line: bool = False
    source: str = ""

    @property
    def type_letter(self) -> str:
        return TYPES.get(self.type, "?")


class BankError(ValueError):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__(f"{len(problems)} problem(s): {problems[:3]}")


def validate(questions: list[Question], answers: bool = False
             ) -> list[str]:
    """Return every problem found. `answers` also checks the answer shape
    the book requires (150 to 450 words, a "A weak answer" line)."""
    problems, seen = [], {}
    for q in questions:
        where = f"{q.qid or '?'} ({q.source})" if q.source else q.qid
        if not q.qid or not QID.match(q.qid):
            problems.append(f"{where}: id must look like Q12.3")
        if q.chapter is None:
            problems.append(f"{where}: no chapter")
        elif not 1 <= q.chapter <= 48:
            problems.append(f"{where}: chapter {q.chapter} out of range")
        elif QID.match(q.qid or "") and int(
                QID.match(q.qid).group(1)) != q.chapter:
            problems.append(f"{where}: id and chapter disagree")
        if q.type not in TYPES:
            problems.append(f"{where}: unknown type {q.type!r}")
        if q.round not in ROUNDS:
            problems.append(f"{where}: unknown round {q.round!r}")
        if q.level not in LEVELS and q.level not in TIERS:
            problems.append(f"{where}: unknown level {q.level!r}")
        for m in q.methods:
            if m not in METHODS:
                problems.append(f"{where}: unknown method {m!r}")
        if not q.text.strip():
            problems.append(f"{where}: empty question")
        if q.qid in seen:
            problems.append(f"{where}: duplicate of {seen[q.qid]}")
        seen.setdefault(q.qid, q.source or q.qid)
        if answers:
            if not 150 <= q.answer_words <= 450:
                problems.append(f"{where}: answer is {q.answer_words}"
                                " words, not 150 to 450")
            if not q.weak_line:
                problems.append(f"{where}: no 'A weak answer' line")
    return problems
