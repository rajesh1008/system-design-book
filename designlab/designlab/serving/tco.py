"""Total cost of ownership: the API bill against a fleet you run.

The API side is the replayed bill: dollars per call at the measured
hit rate, at a pinned price. The self-hosted side is GPUs you hold
for the peak you must serve, plus the people who keep them up. Every
constant below is illustrative and is printed with the result; the
point is the shape of the comparison, not any vendor's price.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .disagg import colocated

HOURS_PER_MONTH = 730
SRE_MONTH_USD = 16000.0      # loaded cost of one engineer, a month
SRE_SHARE = 0.5              # share of one engineer the fleet takes
FLOOR_GPUS = 2               # never fewer than two, for redundancy


@dataclass(frozen=True)
class Fleet:
    gpus: int
    gpu_usd: float
    staff_usd: float

    @property
    def monthly(self) -> float:
        return self.gpu_usd + self.staff_usd


def gpus_for(rate: float, prompt: int, output: int,
             itl_slo_s: float = 0.100, ttft_slo_s: float = 2.0,
             spare: int = 1, limit: int = 512) -> int:
    """Fewest co-located GPUs that hold the rate inside both clocks,
    plus a spare so one failure does not breach them."""
    for g in range(1, limit):
        p = colocated(rate, prompt, output, g)
        if p.stable and p.itl_p95_s <= itl_slo_s \
                and p.ttft_s <= ttft_slo_s:
            return g + spare
    raise ValueError("no fleet size under the limit holds this rate")


def fleet(gpus: int, gpu_hour_usd: float = 3.20,
          sre_share: float = SRE_SHARE) -> Fleet:
    return Fleet(gpus, gpus * gpu_hour_usd * HOURS_PER_MONTH,
                 sre_share * SRE_MONTH_USD)


def break_even_calls(f: Fleet, api_usd_per_call: float) -> float:
    return f.monthly / api_usd_per_call if api_usd_per_call else math.inf
