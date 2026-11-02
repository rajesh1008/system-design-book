"""Three caches and the one that can be wrong.

A prefix cache reuses the model's work on an unchanged prompt prefix
(Chapter 14); the answer is computed fresh every time. A response cache
returns a stored tool or model result for an exact key. A semantic
cache returns a stored answer for a request that is merely similar,
and that is where a near match becomes a wrong answer served fast.

The similarity here is cosine over character trigrams, a stand-in for
an embedding model that keeps the lab offline and deterministic. The
failure it shows does not depend on the embedding: two refund requests
that differ in fare class or date are close in any representation that
also puts paraphrases close.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from common import seeded

FARES = ("basic", "main", "flexible", "premium")
REASONS = ("the airline changed my schedule", "my flight was canceled",
           "I am sick and cannot travel", "my plans changed")
CITIES = ("Denver", "Dallas", "Boston", "Austin", "Newark", "Tampa")
TEMPLATES = (
    "Can I get a refund on my {fare} ticket for the May {day} flight "
    "to {city}? {reason}.",
    "I want a refund for my {fare} fare on May {day} to {city} "
    "because {reason}.",
)


def eligible(fare: str, reason: str) -> str:
    """The refund rule in force (policy version refunds-v4)."""
    if reason.startswith(("the airline", "my flight")):
        return "full refund"
    if fare in ("flexible", "premium"):
        return "full refund"
    if reason.startswith("I am sick"):
        return "credit"
    return "credit" if fare == "main" else "no refund"


@dataclass(frozen=True)
class Ask:
    customer: str
    fare: str
    day: int
    city: str
    reason: str
    text: str

    @property
    def answer(self) -> str:
        return eligible(self.fare, self.reason)


def asks(n: int = 400, seed: int = 18) -> list[Ask]:
    rng = seeded(seed, "cost-semantic", "asks")
    out = []
    for i in range(n):
        fare, reason = rng.choice(FARES), rng.choice(REASONS)
        day, city = rng.randint(10, 20), rng.choice(CITIES)
        text = rng.choice(TEMPLATES).format(
            fare=fare, day=day, city=city,
            reason=reason[0].upper() + reason[1:]
            if rng.random() < 0.5 else reason)
        out.append(Ask(f"T{i:04d}", fare, day, city, reason, text))
    return out


def vec(text: str) -> Counter:
    t = " " + text.lower() + " "
    return Counter(t[i:i + 3] for i in range(len(t) - 2))


def cosine(a: Counter, b: Counter) -> float:
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


def semantic(threshold: float = 0.92, n: int = 400,
             seed: int = 18) -> dict:
    """Serve each request from the closest earlier one above threshold."""
    stored: list[tuple[Ask, Counter]] = []
    served = other = wrong = fare_diff = date_diff = 0
    example = None
    for a in asks(n, seed):
        v = vec(a.text)
        best, sim = None, 0.0
        for b, bv in stored:
            s = cosine(v, bv)
            if s > sim:
                best, sim = b, s
        if best is not None and sim >= threshold:
            served += 1
            other += best.customer != a.customer
            wrong += best.answer != a.answer
            fare_diff += best.fare != a.fare
            date_diff += best.day != a.day
            if example is None and best.answer != a.answer:
                example = (a, best, sim)
            continue
        stored.append((a, v))
    return {"threshold": threshold, "asks": n, "served": served,
            "other_customer": other, "wrong": wrong,
            "fare_diff": fare_diff, "date_diff": date_diff,
            "example": example}


def policy_only(n: int = 400, seed: int = 18,
                version: str = "refunds-v4") -> dict:
    """The safe design: cache only answers with no customer effect,
    keyed by policy version; customer requests always run fresh."""
    cache: dict[tuple, str] = {}
    served = other = 0
    for a in asks(n, seed):
        key = ("policy", version, a.fare)   # "what does a fare allow"
        if key in cache:
            served += 1
        else:
            cache[key] = f"{a.fare} fare rules, {version}"
        # the customer's own refund decision is never looked up here
    return {"policy_answers_served": served, "other_customer": other,
            "entries": len(cache)}


def response_cache(calls: int = 9_000, keys: int = 2_400,
                   seed: int = 18) -> dict:
    """Exact-key fare-rule cache: (carrier, fare basis, policy version).
    Requests follow a Zipf-like popularity over fare bases."""
    rng = seeded(seed, "cost-response", "fare-rules")
    weights = [1.0 / (k + 1) ** 0.9 for k in range(keys)]
    total = sum(weights)
    cum, acc = [], 0.0
    for w in weights:
        acc += w / total
        cum.append(acc)
    seen, hits = set(), 0
    for _ in range(calls):
        r = rng.random()
        lo, hi = 0, keys - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < r:
                lo = mid + 1
            else:
                hi = mid
        if lo in seen:
            hits += 1
        else:
            seen.add(lo)
    return {"calls": calls, "hits": hits, "hit_rate": hits / calls,
            "entries": len(seen)}
