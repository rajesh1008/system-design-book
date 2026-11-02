"""Seeded randomness.

`seeded(seed, "corpus", "itineraries")` gives every table its own stream,
so adding a table never changes the rows of another. Seeds are derived
with SHA-256, not Python's hash(), which changes between processes.
"""
from __future__ import annotations

import hashlib
import random

DEFAULT_SEED = 2026


def derive_seed(seed: int, *labels: str) -> int:
    raw = "|".join([str(seed), *labels]).encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def seeded(seed: int = DEFAULT_SEED, *labels: str) -> random.Random:
    return random.Random(derive_seed(seed, *labels))
