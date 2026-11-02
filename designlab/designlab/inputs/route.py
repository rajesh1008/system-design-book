"""Confidence thresholds and routing, on a seeded population of reads.

Each read has an extractor confidence and, known only to the lab, a
truth bit. The extractor is roughly calibrated with a slight
overconfidence at the top, which is what document and speech models
are usually found to have. For each accept threshold the sweep reports
what share of reads is accepted without a person, the error rate among
those, and the same with a record check (the value must also match a
record Lakeshore controls; a wrong value matches one by chance at a
small rate).
"""
from __future__ import annotations

from dataclasses import dataclass

from common.rand import seeded

CHANCE_MATCH = 0.004     # a wrong identifier that happens to be on file
REVIEW_FLOOR = 0.60      # below this the customer is asked again


@dataclass(frozen=True)
class Read:
    confidence: float
    correct: bool


def population(n: int = 2_000, seed: int = 23) -> list[Read]:
    rng = seeded(seed, "inputs", "reads")
    out = []
    for _ in range(n):
        # most reads are clean scans; some are photos, some are faint
        r = rng.random()
        conf = (rng.betavariate(30, 1.2) if r < 0.70 else
                rng.betavariate(8, 2.5) if r < 0.92 else
                rng.betavariate(3, 3))
        p_ok = min(0.999, conf ** 1.6 + 0.01)
        out.append(Read(round(conf, 3), rng.random() < p_ok))
    return out


def sweep(reads: list[Read], thresholds=(0.5, 0.6, 0.7, 0.8, 0.85,
          0.9, 0.95, 0.97, 0.99), seed: int = 23) -> list[dict]:
    rng = seeded(seed, "inputs", "chance")
    on_file = [r.correct or rng.random() < CHANCE_MATCH for r in reads]
    rows = []
    for t in thresholds:
        acc = [i for i, r in enumerate(reads) if r.confidence >= t]
        err = sum(not reads[i].correct for i in acc)
        chk = [i for i in acc if on_file[i]]
        err_chk = sum(not reads[i].correct for i in chk)
        review = sum(REVIEW_FLOOR <= r.confidence < t for r in reads) \
            + (len(acc) - len(chk))
        rows.append({"t": t, "accepted": len(acc) / len(reads),
                     "err": err / max(1, len(acc)),
                     "accepted_chk": len(chk) / len(reads),
                     "err_chk": err_chk / max(1, len(chk)),
                     "review": review, "ask": sum(
                         r.confidence < REVIEW_FLOOR for r in reads)})
    return rows
