"""How many requests fit in a GPU's KV memory, three ways.

Contiguous: reserve the maximum context for every request up front,
the way a coat check that hands each guest a whole rack would.
Paged: hand out 16-token blocks as the request grows, and keep a block
table per request, the way a cloakroom hands out hooks. Paged with a
shared prefix: requests that start with the same blocks point at the
same hooks, and the shared blocks are counted once.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .clocks import kv_bytes_per_token


@dataclass(frozen=True)
class Fit:
    scheme: str
    requests: int
    used_tokens: int
    reserved_tokens: int

    @property
    def waste(self) -> float:
        """Share of held memory no request is using. Zero once a shared
        prefix makes one held block serve many requests."""
        r = self.reserved_tokens
        return max(0.0, (r - self.used_tokens) / r) if r else 0.0

    @property
    def served_per_held(self) -> float:
        """Tokens of context served for each token of memory held."""
        r = self.reserved_tokens
        return self.used_tokens / r if r else 0.0


def fit(lengths: list[int], kv_gib: float = 60.0, max_context: int = 16384,
        block: int = 16, shared_prefix: int = 0,
        per_token: int | None = None) -> list[Fit]:
    """Admit requests in order until memory runs out, per scheme."""
    per = per_token or kv_bytes_per_token()
    cap = int(kv_gib * 2**30 // per)
    out = []
    # contiguous
    n = used = 0
    for ln in lengths:
        if (n + 1) * max_context > cap:
            break
        n, used = n + 1, used + ln
    out.append(Fit("contiguous", n, used, n * max_context))
    # paged
    n = used = held = 0
    for ln in lengths:
        need = math.ceil(ln / block) * block
        if held + need > cap:
            break
        n, used, held = n + 1, used + ln, held + need
    out.append(Fit("paged", n, used, held))
    # paged, shared prefix counted once
    shared = (shared_prefix // block) * block
    n, used, held = 0, 0, shared
    for ln in lengths:
        need = math.ceil((ln - shared) / block) * block
        if held + need > cap:
            break
        n, used, held = n + 1, used + ln, held + need
    out.append(Fit("paged+prefix", n, used + shared, held))
    return out
