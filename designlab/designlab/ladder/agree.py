"""Agreement between two scorers on the same answers.

`exact` is the share of criterion cells (answers times seven) where
both scorers wrote the same number. `kappa` is Cohen's kappa over the
same cells, which discounts the agreement two scorers would reach by
chance from how often each uses 0, 1, and 2.
"""
from __future__ import annotations

from collections import Counter


def cells(a: dict[str, list[int]], b: dict[str, list[int]],
          ids: list[str] | None = None,
          col: int | None = None) -> list[tuple[int, int]]:
    ids = ids or sorted(set(a) & set(b))
    out = []
    for i in ids:
        ra, rb = a[i], b[i]
        rng = [col] if col is not None else range(len(ra))
        out.extend((ra[k], rb[k]) for k in rng)
    return out


def exact(pairs: list[tuple[int, int]]) -> tuple[int, int]:
    return sum(1 for x, y in pairs if x == y), len(pairs)


def kappa(pairs: list[tuple[int, int]]) -> float:
    n = len(pairs)
    if not n:
        return 0.0
    po = sum(1 for x, y in pairs if x == y) / n
    ca = Counter(x for x, _ in pairs)
    cb = Counter(y for _, y in pairs)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)
