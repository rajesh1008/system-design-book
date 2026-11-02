"""Two prefix caches over the same chained hash.

The identity of a prefix is a hash chain: each segment's hash covers
its parent's hash and its own key, and the first link covers a salt.
Change one early segment and every later hash changes with it, which
is why a timestamp at the top of a prompt empties the cache.

`PromptCache` behaves like a provider's prompt cache: entries are
written only at breakpoints, a read looks back at most 20 segments
from each breakpoint, an entry lives 5 minutes from its last use, and
an entry is readable only once the call that wrote it has started to
answer. `EngineCache` behaves like a self-hosted engine's cache:
every full block is kept until memory runs out, and the least
recently used block goes first.
"""
from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass

from .layout import Rendered
from .prices import Bill

LOOKBACK = 20
TTL_S = 300.0
MIN_TOKENS = 512


def chain(segs, salt: str = "") -> list[str]:
    out, h = [], hashlib.sha256(salt.encode()).hexdigest()
    for s in segs:
        h = hashlib.sha256(f"{h}|{s.key}".encode()).hexdigest()
        out.append(h)
    return out


def cumulative(segs) -> list[int]:
    out, n = [], 0
    for s in segs:
        n += s.tokens
        out.append(n)
    return out


@dataclass
class Entry:
    live_from: float
    expires: float
    ttl: float = TTL_S


class PromptCache:
    """A provider-style cache: breakpoints, lookback, time to live."""

    def __init__(self, ttl_s: float = TTL_S, lookback: int = LOOKBACK,
                 first_token_s: float = 1.0):
        self.ttl, self.lookback, self.lag = ttl_s, lookback, first_token_s
        self.entries: dict[str, Entry] = {}

    def call(self, r: Rendered, now: float, output: int,
             salt: str = "") -> Bill:
        hs, cum = chain(r.segs, salt), cumulative(r.segs)
        best = -1
        for b in r.breakpoints:
            for i in range(b, max(-1, b - self.lookback), -1):
                e = self.entries.get(hs[i])
                if e and e.live_from <= now < e.expires:
                    best = max(best, i)
                    break
        read = cum[best] if best >= 0 else 0
        ttls = list(r.ttls) or [self.ttl] * len(r.breakpoints)
        w5 = w1 = 0
        done = read
        for b, ttl in sorted(zip(r.breakpoints, ttls)):
            if b <= best or cum[b] < MIN_TOKENS:
                continue
            self.entries[hs[b]] = Entry(now + self.lag, now + ttl, ttl)
            if ttl > TTL_S:
                w1 += cum[b] - done
            else:
                w5 += cum[b] - done
            done = cum[b]
        if best >= 0:
            e = self.entries[hs[best]]
            e.expires = max(e.expires, now + e.ttl)
        uncached = r.tokens - done
        return Bill(uncached=uncached, written=w5, read=read,
                    output=output, written_1h=w1)


class EngineCache:
    """An engine-style cache: full blocks, LRU, bounded memory.

    block=16 is a hash-per-block engine; block=1 behaves like a
    radix tree that can share any token-length prefix.
    """

    def __init__(self, capacity_tokens: int, block: int = 16):
        self.cap, self.block = capacity_tokens, block
        self.lru: OrderedDict[str, int] = OrderedDict()
        self.held = 0

    def call(self, r: Rendered, now: float, output: int,
             salt: str = "") -> Bill:
        hs, cum = chain(r.segs, salt), cumulative(r.segs)
        matched = 0
        for i, h in enumerate(hs):
            if h not in self.lru:
                break
            self.lru.move_to_end(h)
            matched = cum[i]
        matched -= matched % self.block
        prev = 0
        for i, h in enumerate(hs):
            if h not in self.lru:
                self.lru[h] = cum[i] - prev
                self.held += cum[i] - prev
            prev = cum[i]
        while self.held > self.cap and self.lru:
            _, n = self.lru.popitem(last=False)
            self.held -= n
        return Bill(uncached=r.tokens - matched, read=matched,
                    output=output)
