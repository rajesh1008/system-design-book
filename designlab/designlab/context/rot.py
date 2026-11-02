"""Context rot: the same task gets worse as the context around it grows.

`success_at` is the lab's stand-in for the model: a curve that falls
slowly and then faster past a knee. The harness does what Hannah's
team did on Thursday, May 7: fix a set of pilot tasks, pad each with
real history from other runs (never with filler), vary only the
length, and fit two straight lines to find where the slope changes.
"""
from __future__ import annotations

import math

from common.rand import seeded

BASE = 0.968
SLOPE = 0.15e-6          # per token, all the way
KNEE, STEEP, SOFT = 60_000, 1.45e-6, 6_000   # extra slope past the knee
LENGTHS = tuple(range(10_000, 130_001, 10_000))
TRIALS = 600             # fixed pilot tasks per length


def success_at(tokens: float) -> float:
    past = SOFT * math.log1p(math.exp((tokens - KNEE) / SOFT))
    return BASE - SLOPE * tokens - STEEP * past


def harness(seed: int = 21, lengths=LENGTHS, trials: int = TRIALS):
    """[(length, successes, trials)], the same tasks at every length."""
    out = []
    for L in lengths:
        r = seeded(seed, "rot", str(L))
        ok = sum(r.random() < success_at(L) for _ in range(trials))
        out.append((L, ok, trials))
    return out


def _line(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx \
        if sxx else 0.0
    a = my - b * mx
    return a, b, sum((y - a - b * x) ** 2 for x, y in zip(xs, ys))


def knee(points) -> int:
    """The break that best splits the curve into two straight lines
    (each with at least three points), and where the right line is the
    steeper. Returns the length at the break."""
    xs = [p[0] for p in points]
    ys = [p[1] / p[2] for p in points]
    best, at = None, xs[0]
    for i in range(2, len(xs) - 3):
        _, b1, e1 = _line(xs[:i + 1], ys[:i + 1])
        _, b2, e2 = _line(xs[i:], ys[i:])
        if b2 >= b1:
            continue
        if best is None or e1 + e2 < best:
            best, at = e1 + e2, xs[i]
    return at


def budget_from(knee_tokens: int, margin: float = 0.20,
                step: int = 1_000) -> int:
    """The per-step budget: a margin below the knee, rounded down."""
    return int(knee_tokens * (1 - margin)) // step * step
