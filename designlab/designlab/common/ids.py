"""Run ids: sortable by time, reproducible under a seed."""
from __future__ import annotations

import random

from .clock import Clock, SystemClock


def run_id(prefix: str = "run", clock: Clock | None = None,
           rng: random.Random | None = None) -> str:
    """For example run-20260105T090000-3f9a1c."""
    t = (clock or SystemClock()).now()
    r = rng or random.Random()
    return f"{prefix}-{t:%Y%m%dT%H%M%S}-{r.getrandbits(24):06x}"
