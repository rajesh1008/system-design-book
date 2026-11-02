"""pass@k and pass^k from n trials per task.

pass@k: the chance that at least one of k trials succeeds, the
measure for a tool that a person retries. pass^k: the chance that all
k succeed, the measure for an agent that acts on every request once.
Both are the unbiased estimates over n >= k trials with c successes,
averaged over tasks.
"""
from __future__ import annotations

from math import comb


def pass_at_k(n: int, c: int, k: int) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    return comb(c, k) / comb(n, k)


def table(counts: list[int], n: int, ks=range(1, 9)) -> list[tuple]:
    """counts: successes per task out of n. Rows of (k, pass@k, pass^k)."""
    m = len(counts)
    return [(k, sum(pass_at_k(n, c, k) for c in counts) / m,
             sum(pass_hat_k(n, c, k) for c in counts) / m) for k in ks]
