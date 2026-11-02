"""The context card: one row per thing the chapter asked to be
measured, a target, the measured value, and a check. The highlighted
cell is success on the longest runs, the cell that changed a decision.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from .compact import Result
from .runs import bucket

HIGHLIGHT = "success, 17-24 steps"


@dataclass
class Row:
    name: str
    target: str
    value: str
    ok: bool


def success(results: list[Result], b: str) -> float:
    got = [x for x in results if bucket(x.length) == b]
    return 100 * sum(x.success for x in got) / len(got)


def unnoticed(results: list[Result], per_step: int) -> int:
    """Steps over the budget that raised no alarm."""
    n = 0
    for x in results:
        over = sum(t > per_step for t in x.tokens)
        alarmed = sum(a.startswith("budget") for a in x.alarms)
        n += max(0, over - alarmed)
    return n


def rows(before: list[Result], after: list[Result], per_step: int,
         trigger: int, knee: int, instr: tuple[str, int, int]):
    p95 = sorted(x.peak for x in after)[int(0.95 * len(after)) - 1]
    over = sum(sum(t > per_step for t in x.tokens) for x in after)
    alarms = sum(len(x.alarms) for x in after)
    lost = sum(bool(x.lost) for x in after)
    cards = sum(x.second_card for x in after)
    short, long_ = success(after, "1-4"), success(after, "17-24")
    was = success(before, "17-24")
    miss = unnoticed(after, per_step)
    comps = sum(x.compactions for x in after)
    ran = sum(bool(x.compactions) for x in after)
    return [
        Row("budget a step", f"below knee {knee:,}", f"{per_step:,}",
            per_step < knee),
        Row("compaction at", "below the budget",
            f"{trigger:,} ({100 * trigger / per_step:.0f}%)",
            trigger < per_step),
        Row("compactions", "as few as hold", f"{comps:,} in {ran:,} runs",
            True),
        Row("peak context, p95", f"<= {per_step:,}", f"{p95:,}",
            p95 <= per_step),
        Row("steps over budget", "every one alarmed",
            f"{over} ({alarms} alarms)", miss == 0),
        Row("unnoticed breaches", "0", f"{miss}", miss == 0),
        Row("runs that lost a fact", "0", f"{lost}", lost == 0),
        Row("second approval cards", "0", f"{cards}", cards == 0),
        Row("success, 1-4 steps", "baseline", f"{short:.1f}%", True),
        Row(HIGHLIGHT, "within 2 pts of 1-4",
            f"{long_:.1f}% (was {was:.1f}%)", short - long_ <= 2.0),
        Row("instruction file", "0 stale, 0 unowned",
            f"{instr[0]}, {instr[1]:,} tok, {instr[2]} findings",
            instr[2] == 0),
    ]


def peak_median(results: list[Result]) -> int:
    return int(statistics.median(x.peak for x in results))
