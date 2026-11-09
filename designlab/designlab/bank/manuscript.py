"""Read every chapter's interview section into one bank (Chapter 47).

    python3 -m bank.manuscript [--root DIR]

The manuscript is the source of truth: each chapter's `{.qa}` blocks
carry the type, round, and level tags, and the heading carries the ID.
`scan` parses them with the v0 loader, counts the raw block openings
per chapter as a cross-check, and keeps the heading text so the round
router can read it. The public repository ships the code without the
manuscript, so `snapshot` writes (and `load_snapshot` reads) a
tab-separated index with the tags and the routed round, never the
question text or the answers.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .loader import OPEN, parse_markup
from .schema import BankError, Question, validate

ROOT = Path(__file__).resolve().parents[3] / "02-manuscript"
SNAPSHOT = Path(__file__).with_name("data") / "bank-index.tsv"
CHAPTER_FILE = re.compile(r"^ch(\d\d)\.md$")
COLUMNS = ("qid", "chapter", "type", "round", "level", "loop_round",
           "rule", "hiring_side", "answer_words", "weak_line")


@dataclass
class Scan:
    questions: list[Question]
    raw: dict[int, int] = field(default_factory=dict)
    files: dict[int, str] = field(default_factory=dict)

    @property
    def chapters(self) -> list[int]:
        return sorted(self.raw)

    def per_chapter(self) -> dict[int, int]:
        out = {c: 0 for c in self.raw}
        for q in self.questions:
            if q.chapter in out:
                out[q.chapter] += 1
        return out

    def problems(self, answers: bool = True) -> list[str]:
        """Schema problems plus any chapter whose raw block count and
        parsed count disagree (a block the loader could not read)."""
        out = validate(self.questions, answers=answers)
        parsed = self.per_chapter()
        for ch, n in sorted(self.raw.items()):
            if parsed.get(ch, 0) != n:
                out.append(f"ch{ch:02d}: {n} blocks, "
                           f"{parsed.get(ch, 0)} parsed")
        return out


def chapter_files(root: Path = ROOT) -> list[tuple[int, Path]]:
    out = []
    for p in sorted(Path(root).glob("ch*.md")):
        m = CHAPTER_FILE.match(p.name)
        if m:
            out.append((int(m.group(1)), p))
    return out


def scan(root: Path = ROOT, extra: dict[int, str] | None = None
         ) -> Scan:
    """Parse every chapter file under `root`. `extra` maps a chapter
    number to replacement text (used by tests and fault injection)."""
    s = Scan(questions=[])
    texts = {ch: p.read_text(encoding="utf-8")
             for ch, p in chapter_files(root)}
    texts.update(extra or {})
    for ch in sorted(texts):
        text = texts[ch]
        name = f"ch{ch:02d}.md"
        s.raw[ch] = sum(1 for ln in text.splitlines() if OPEN.match(ln))
        s.files[ch] = name
        try:
            s.questions += parse_markup(text, name)
        except BankError as exc:
            raise BankError([f"{name}: {p}" for p in exc.problems])
    return s


def snapshot(rows: list[dict], path: Path = SNAPSHOT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t",
                           lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: int(r[k]) if isinstance(r[k], bool) else r[k]
                        for k in COLUMNS})
    return path


def load_snapshot(path: Path = SNAPSHOT) -> list[dict]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        r["chapter"] = int(r["chapter"]) if r["chapter"] else None
        r["answer_words"] = int(r["answer_words"])
        r["hiring_side"] = r["hiring_side"] == "1"
        r["weak_line"] = r["weak_line"] == "1"
    return rows


def available(root: Path = ROOT) -> bool:
    return bool(chapter_files(root))
