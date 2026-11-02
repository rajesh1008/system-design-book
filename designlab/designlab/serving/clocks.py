"""Three clocks of one model call, and Little's law for the fleet.

Time to first token is queue plus prefill of the tokens the cache did
not already hold. Inter-token latency is one decode step. End to end
is the first plus the rest of the output at the second.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Clocks:
    ttft_s: float
    itl_s: float
    e2e_s: float


def three_clocks(queue_s: float, prompt: int, cached: int, output: int,
                 prefill_tok_s: float, itl_s: float) -> Clocks:
    prefill = (prompt - cached) / prefill_tok_s
    ttft = queue_s + prefill
    return Clocks(ttft, itl_s, ttft + max(output - 1, 0) * itl_s)


def decode_step_s(batch: int, base_ms: float, per_seq_ms: float) -> float:
    """A decode step reads the weights once for the whole batch (the
    base) and each sequence's KV cache (the per-sequence part)."""
    return (base_ms + per_seq_ms * batch) / 1000.0


def in_flight(arrivals_per_s: float, seconds_each: float) -> float:
    """Little's law: L = lambda x W."""
    return arrivals_per_s * seconds_each


def kv_bytes_per_token(layers: int = 32, kv_heads: int = 8,
                       head_dim: int = 128, bytes_each: int = 2) -> int:
    """Keys and values, every layer: 2 x layers x heads x dim x bytes.
    The defaults are an 8B-class model with grouped KV heads at 16-bit:
    131,072 bytes, 128 KiB a token."""
    return 2 * layers * kv_heads * head_dim * bytes_each


def kv_gib(sequences: float, tokens_each: float,
           per_token: int | None = None) -> float:
    per = per_token or kv_bytes_per_token()
    return sequences * tokens_each * per / 2**30
