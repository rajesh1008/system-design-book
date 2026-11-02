"""Speculative decoding: when a draft helps and when it costs.

A draft proposes k tokens; the target model checks all of them in one
pass and keeps the longest run it agrees with, plus one of its own.
With acceptance rate a and draft cost c (a draft step as a share of a
target step), the expected speed-up at batch 1 is the published
expression (1 - a**(k+1)) / ((1 - a) * (k*c + 1)).

At larger batches the verify pass stops being nearly free: the GPU is
busy with real work, and checking k extra tokens per sequence costs
compute. `speedup` charges that with the same decode model as the rest
of the lab plus a per-token compute term. Illustrative constants.
"""
from __future__ import annotations

from common import seeded


def expected_tokens(a: float, k: int) -> float:
    """Tokens produced per verify pass, accepted run plus one."""
    if a >= 1.0:
        return k + 1.0
    return (1 - a ** (k + 1)) / (1 - a)


def formula(a: float, k: int, c: float) -> float:
    return expected_tokens(a, k) / (k * c + 1)


def speedup(a: float, k: int, c: float, batch: int,
            base_ms: float = 17.5, per_seq_ms: float = 0.34,
            per_tok_ms: float = 0.12) -> float:
    plain = base_ms + per_seq_ms * batch + per_tok_ms * batch
    verify = base_ms + per_seq_ms * batch + per_tok_ms * batch * (k + 1)
    draft = k * c * plain
    return expected_tokens(a, k) * plain / (verify + draft)


def simulate(a: float, k: int, passes: int = 20000, seed: int = 14
             ) -> float:
    """Monte Carlo tokens per pass, to check expected_tokens."""
    r = seeded(seed, "serving", "speculative")
    total = 0
    for _ in range(passes):
        run = 0
        while run < k and r.random() < a:
            run += 1
        total += run + 1
    return total / passes


def best_k(a: float, c: float, batch: int, ks=range(1, 9)) -> tuple:
    return max(((k, speedup(a, k, c, batch)) for k in ks),
               key=lambda x: x[1])
