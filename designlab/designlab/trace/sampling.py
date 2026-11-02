"""What to keep, and what keeping costs.

Tail sampling decides after the trace is finished, so the collector
holds every span of every open trace until the decision. The buffer is
rate x size x wait, plus whatever piles up while the exporter is
stalled. Keeping every error and every effect makes a biased sample;
a small random stream, with its inclusion probability written on each
kept trace, is what rates are estimated from.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass


def buffer_bytes(spans_per_s: float, bytes_per_span: float,
                 wait_s: float, pause_s: float = 0.0) -> dict:
    live = spans_per_s * bytes_per_span * wait_s
    pause = spans_per_s * bytes_per_span * pause_s
    return {"live": live, "pause": pause, "total": live + pause}


def per_replica(total: float, replicas: int, overhead: float = 2.5,
                spare: int = 1) -> float:
    """Memory one collector replica needs: its share with one replica
    lost (N+1), times the in-memory overhead of span objects."""
    return total / replicas * (replicas / (replicas - spare)) * overhead


@dataclass(frozen=True)
class Keep:
    keep: bool
    why: str
    p: float          # inclusion probability, written on the trace


RANDOM_P = 0.05


def u(trace_id: str) -> float:
    return int(hashlib.sha256(trace_id.encode()).hexdigest()[:8],
               16) / 2 ** 32


def in_random(trace_id: str, p: float = RANDOM_P) -> bool:
    """The random stream: drawn over every trace, whatever else keeps
    it, so it is the one unbiased sample of the day."""
    return u(trace_id) < p


def decide(root_attrs: dict, has_effect: bool, has_error: bool,
           trace_id: str, p: float = RANDOM_P) -> Keep:
    """Effects kept by a head decision (known when the run starts to
    act), errors and hand-offs by a tail decision, the rest only if
    the random stream drew them."""
    if has_effect:
        return Keep(True, "effect", 1.0)
    if has_error or root_attrs.get("lakeshore.outcome") == "handed_off":
        return Keep(True, "error_or_handoff", 1.0)
    if in_random(trace_id, p):
        return Keep(True, "random", p)
    return Keep(False, "dropped", p)


def wilson(k: int, n: int, z: float = 1.96,
           deff: float = 1.0) -> tuple[float, float]:
    """Wilson interval for k of n, widened by a design effect."""
    if n == 0:
        return (0.0, 1.0)
    n_eff = n / deff
    ph = k / n
    den = 1 + z * z / n_eff
    mid = (ph + z * z / (2 * n_eff)) / den
    half = z * math.sqrt(ph * (1 - ph) / n_eff
                         + z * z / (4 * n_eff * n_eff)) / den
    return (max(0.0, mid - half), min(1.0, mid + half))
