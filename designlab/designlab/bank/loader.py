"""Read questions from chapter markup or from the bank's table format.

Chapter markup (the Interview Voice Reference):

    :::: {.qa type="concept" round="system-design" level="senior"}
    **Q2.1 The question text.**

    Answer paragraphs...

    A weak answer ...
    ::::

Bank format (02-manuscript/interview-bank.md), one row per question:

    | ID | Chapter | Type | Round | Level | Competency | Methods | Question |
"""
from __future__ import annotations

import re
from pathlib import Path

from .schema import QID, BankError, Question, validate
from .taxonomy import norm_type

OPEN = re.compile(r"^::::\s*\{\.qa\b(?P<attrs>[^}]*)\}\s*$")
CLOSE = re.compile(r"^::::\s*$")
ATTR = re.compile(r'(\w+)="([^"]*)"')
HEAD = re.compile(r"^\*\*(Q\d{1,2}\.\d{1,2})\s+(.+?)\*\*\s*$")


def _split(value: str) -> list[str]:
    return [v.strip() for v in re.split(r"[;,]", value) if v.strip()]


def _chapter(qid: str, attrs: dict) -> int | None:
    if attrs.get("chapter", "").strip().isdigit():
        return int(attrs["chapter"])
    m = QID.match(qid or "")
    return int(m.group(1)) if m else None


def parse_markup(text: str, source: str = "") -> list[Question]:
    out, cur, body = [], None, []
    for n, line in enumerate(text.splitlines(), 1):
        if cur is None:
            m = OPEN.match(line)
            if m:
                cur = {"attrs": dict(ATTR.findall(m["attrs"])),
                       "line": n}
                body = []
            continue
        if CLOSE.match(line):
            out.append(_from_block(cur, body, source))
            cur = None
        else:
            body.append(line)
    if cur is not None:
        raise BankError([f"{source}:{cur['line']}: unclosed .qa block"])
    return out


def _from_block(cur: dict, body: list[str], source: str) -> Question:
    attrs = cur["attrs"]
    qid, text, rest = "", "", []
    for line in body:
        m = HEAD.match(line.strip()) if not qid else None
        if m:
            qid, text = m.group(1), m.group(2)
        elif qid:
            rest.append(line)
    answer = " ".join(rest)
    return Question(
        qid=qid, chapter=_chapter(qid, attrs),
        type=norm_type(attrs.get("type", "")),
        round=attrs.get("round", "").strip(),
        level=attrs.get("level", "").strip(), text=text,
        competency=_split(attrs.get("tags", "")),
        methods=_split(attrs.get("method", "")),
        answer_words=len(answer.split()),
        weak_line="A weak answer" in answer,
        source=f"{source}:{cur['line']}")


def parse_table(text: str, source: str = "") -> list[Question]:
    out, header = [], None
    for n, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        if "id" not in row:
            continue
        ch = row.get("chapter", "")
        out.append(Question(
            qid=row["id"], chapter=int(ch) if ch.isdigit() else None,
            type=norm_type(row.get("type", "")),
            round=row.get("round", ""), level=row.get("level", ""),
            text=row.get("question", ""),
            competency=_split(row.get("competency", "")),
            methods=_split(row.get("methods", "")),
            source=f"{source}:{n}"))
    return out


def load(path: Path, check: bool = True) -> list[Question]:
    """Load a file in either format; raise BankError if any question
    fails validation."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    qs = parse_markup(text, path.name) if "{.qa" in text \
        else parse_table(text, path.name)
    if check:
        problems = validate(qs)
        if problems:
            raise BankError(problems)
    return qs
