"""A toy prefill/decode split. Not a simulator; a way to ask the
question with numbers before anyone rents a second pool.

Co-located: every GPU runs both phases; prefill is chunked so a long
prompt does not freeze decoding, but each chunk lengthens the decode
step it rides on. Disaggregated: prefill GPUs and decode GPUs are
separate pools, and each finished prompt's KV cache crosses the
network to a decode GPU before the first token.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .clocks import decode_step_s, kv_bytes_per_token


@dataclass(frozen=True)
class Pool:
    ttft_s: float
    itl_mean_s: float
    itl_p95_s: float
    decode_batch: float
    stable: bool


def _decode(rate: float, output: int, base_ms: float, per_seq_ms: float,
            extra_s: float = 0.0) -> tuple[float, float]:
    """Solve b = rate x output x step(b) by fixed point."""
    b = 1.0
    for _ in range(200):
        step = decode_step_s(b, base_ms, per_seq_ms) + extra_s
        b = rate * output * step
        if b > 4096:
            break
    return b, decode_step_s(b, base_ms, per_seq_ms) + extra_s


def erlang_c_wait(rate: float, service_s: float, servers: int) -> float:
    """Mean queue wait in an M/M/c queue (Erlang C)."""
    a = rate * service_s
    if a >= servers:
        return float("inf")
    term, total = 1.0, 1.0
    for k in range(1, servers):
        term *= a / k
        total += term
    top = term * a / servers / (1 - a / servers)
    p_wait = top / (total + top)
    return p_wait * service_s / (servers - a)


def colocated(rate: float, prompt: int, output: int, gpus: int,
              prefill_tok_s: float = 11800, base_ms: float = 17.5,
              per_seq_ms: float = 0.34, chunk: int = 512,
              max_batch: int = 64) -> Pool:
    per = rate / gpus
    chunk_s = chunk / prefill_tok_s
    share = min(1.0, per * prompt / prefill_tok_s)   # prefill busy share
    b, step = _decode(per, output, base_ms, per_seq_ms, share * chunk_s)
    plain = decode_step_s(b, base_ms, per_seq_ms)
    p95 = plain + chunk_s if share > 0.05 else step
    ttft = math.ceil(prompt / chunk) * (plain + chunk_s)
    return Pool(ttft, step, p95, b, share < 0.9 and b <= max_batch)


def split(rate: float, prompt: int, output: int, prefill_gpus: int,
          decode_gpus: int, prefill_tok_s: float = 11800,
          base_ms: float = 17.5, per_seq_ms: float = 0.34,
          link_gb_s: float = 12.5, max_batch: int = 64) -> Pool:
    rho = rate * prompt / (prefill_gpus * prefill_tok_s)
    service = prompt / prefill_tok_s
    wait = erlang_c_wait(rate, service, prefill_gpus)
    transfer = prompt * kv_bytes_per_token() / (link_gb_s * 1e9)
    b, step = _decode(rate / decode_gpus, output, base_ms, per_seq_ms)
    return Pool(service + wait + transfer, step, step, b,
                rho < 0.9 and b <= max_batch)


def best_split(rate: float, prompt: int, output: int, gpus: int,
               **kw) -> tuple[int, Pool] | None:
    """The stable split with the lowest TTFT, if any."""
    best = None
    for gp in range(1, gpus):
        p = split(rate, prompt, output, gp, gpus - gp, **kw)
        if p.stable and (best is None or p.ttft_s < best[1].ttft_s):
            best = (gp, p)
    return best
