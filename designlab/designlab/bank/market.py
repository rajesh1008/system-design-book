"""Read the job-market skill list and tag each posting (Chapter 41).

The fixture (fixtures/job-market.md) is a paraphrase of the book's
job-market matrix as of November 2, 2026: company, segment, month,
title, the skills and deliverables a posting names, and the published
salary band. Tagging is by keyword into the six skills Chapter 41
uses for the team (plus "field" for customer-facing work). It is a
reading aid, not a labor-market study: one sweep, 47 postings.

    python3 -m bank.market
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

FIXTURE = Path(__file__).with_name("fixtures") / "job-market.md"

SKILLS = ("distributed", "models", "retrieval", "control",
          "evaluation", "operations")
TAGS = SKILLS + ("field",)

# Lowercase substrings. Order does not matter; a posting can carry
# many tags. Kept short so a reader can audit every match.
KEYWORDS: dict[str, tuple[str, ...]] = {
    "distributed": ("distributed", "durable", "runtime", "execution",
                    "orchestrat", "infrastructure", "serving",
                    "inference", "backend", "long-running", "scale",
                    "workflow", "a2a", "mcp", "protocol"),
    "models": ("model", "prompt", "context", "applied ml", "llm",
               "claude", "openai apis", "genai"),
    "retrieval": ("retrieval", "rag", "vector", "data", "memory",
                  "query"),
    "control": ("guardrail", "security", "secure", "policy",
                "permission", "tenancy", "cost control"),
    "evaluation": ("eval", "judge", "golden", "regression", "quality",
                   "test harness", "simulation"),
    "operations": ("observability", "telemetry", "trac", "monitor",
                   "reliability", "agentops", "genaiops", "mlops",
                   "operating practice"),
    "field": ("customer", "partner", "travel", "engagement",
              "field"),
}

ROW = re.compile(r"^\|\s*(\d+)\s*\|")
USD = re.compile(r"\$(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)K")


@dataclass(frozen=True)
class Posting:
    row: int
    company: str
    segment: str
    month: str
    title: str
    skills: str
    salary: str
    tags: frozenset = field(default_factory=frozenset)

    def usd_band(self) -> tuple[float, float] | None:
        """First US-dollar band, in thousands; None if none."""
        m = USD.search(self.salary)
        return (float(m.group(1)), float(m.group(2))) if m else None


def tag(text: str) -> frozenset:
    low = text.lower()
    return frozenset(t for t in TAGS
                     if any(k in low for k in KEYWORDS[t]))


def load(path: Path = FIXTURE) -> list[Posting]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            raise ValueError(f"row needs 7 cells: {line[:40]}")
        n, co, seg, mo, title, skills, sal = cells
        out.append(Posting(int(n), co, seg, mo, title, skills, sal,
                           tag(f"{title}; {skills}")))
    return out


def counts(ps: list[Posting]) -> dict[str, int]:
    return {t: sum(t in p.tags for p in ps) for t in TAGS}


def both(ps: list[Posting], *tags: str) -> list[Posting]:
    return [p for p in ps if all(t in p.tags for t in tags)]


def segments(ps: list[Posting]) -> dict[str, list[Posting]]:
    out: dict[str, list[Posting]] = {}
    for p in ps:
        out.setdefault(p.segment, []).append(p)
    return out


def midpoint_k(ps: list[Posting]) -> float | None:
    """Median of US-dollar band midpoints, in thousands."""
    mids = [(b[0] + b[1]) / 2 for p in ps if (b := p.usd_band())]
    return median(mids) if mids else None


def main() -> None:
    from common.text import emit
    ps = load()
    emit(f"postings {len(ps)}, employers "
         f"{len({p.company for p in ps})}")
    c = counts(ps)
    for t in TAGS:
        emit(f"  {t:<12}{c[t]:>4}  {c[t] / len(ps):>4.0%}")


if __name__ == "__main__":
    main()
