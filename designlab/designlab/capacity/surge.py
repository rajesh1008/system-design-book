"""Capacity for the surge: size sessions, model slots, and the token
limit for Monday 8 to 10 a.m. at the design ceiling, then replay it.

The ceiling is every contact about a change, new or follow-up:
2.10 million plus 2.24 million a year (Chapter 4's baseline).
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from statistics import NormalDist

from common.rand import seeded

from .estimate import Fit, estimate
from .queue import minutes_over, slots_for

CEILING_PER_YEAR = 4_340_000
FORECAST_MARGIN = 1.25      # the ceiling forecast may be this far low
RARE = 1e-4                 # "almost never": one minute in 10,000
STORM_CHANGES_PER_S = 1.86  # Chapter 5's Estimate Sheet


def _up(x: float, step: float) -> float:
    return math.ceil(x / step - 1e-9) * step


@dataclass(frozen=True)
class SurgePlan:
    mean_per_hour: float
    surge_per_hour: float
    planned_per_s: float        # surge rate times the forecast margin
    sessions_mean: float        # Little's law at the planned rate
    sessions: int               # size to buy, rounded up to tens
    calls_per_s: float
    calls_offered: float        # Erlangs: calls per s x seconds each
    model_slots: int
    tpm_mean: float             # input tokens a minute, planned rate
    tpm_limit: float            # limit to buy, rounded up to 0.1M
    limit_util: float
    minutes_over_limit: float


def size_surge(fit: Fit, per_year: float = CEILING_PER_YEAR,
               margin: float = FORECAST_MARGIN) -> SurgePlan:
    mean_h = per_year / (365 * 24)
    surge_h = mean_h * fit.surge_ratio
    e = estimate(fit, surge_h * margin)
    z = NormalDist().inv_cdf(1 - RARE)
    # Sessions in flight at any instant are Poisson around Little's L.
    n = int(_up(e.sessions_in_flight
                + z * math.sqrt(e.sessions_in_flight), 10))
    offered = e.model_calls_per_s * fit.call_mean_s
    cpm = e.model_calls_per_s * 60
    sd_min = math.sqrt(cpm * (fit.tokens_in ** 2 + fit.tokens_in_sd ** 2))
    limit = _up(e.tokens_in_per_min + z * sd_min, 100_000)
    return SurgePlan(
        mean_per_hour=mean_h, surge_per_hour=surge_h,
        planned_per_s=e.sessions_per_s,
        sessions_mean=e.sessions_in_flight, sessions=n,
        calls_per_s=e.model_calls_per_s, calls_offered=offered,
        model_slots=slots_for(offered),
        tpm_mean=e.tokens_in_per_min, tpm_limit=limit,
        limit_util=e.tokens_in_per_min / limit,
        minutes_over_limit=minutes_over(limit, cpm, fit.tokens_in,
                                        fit.tokens_in_sd))


def residences(sessions) -> list[float]:
    """Session open to close, seconds, for every traced session."""
    out = []
    for s in sessions:
        work = sum(sum(x.model_s) + x.error_s + x.wait_own
                   + sum(x.tool_s) + sum(x.gate_s) + x.trail_s + x.loop_s
                   for x in s.steps)
        out.append(s.knowledge_s + work + s.customer_s + s.approval_s
                   + s.idle_s)
    return out


@dataclass(frozen=True)
class LoadReplay:
    hours: float
    arrivals: int
    peak: int                   # most sessions open at once
    refused: int                # arrivals that found every slot taken


def load_replay(sessions, rate_per_s: float, slots: int,
                hours: float = 2.0, warm_s: float = 3600.0,
                seed: int = 0) -> LoadReplay:
    """Poisson arrivals at rate_per_s, each holding a slot for a
    residence drawn from the traces. One hour of warm-up at the same
    rate fills the system before the two measured hours start."""
    rng = seeded(seed, "capacity-load-replay")
    pool = residences(sessions)
    t, end = -warm_s, hours * 3600
    open_until: list[float] = []
    arrivals = peak = refused = 0
    while True:
        t += rng.expovariate(rate_per_s)
        if t >= end:
            break
        while open_until and open_until[0] <= t:
            heapq.heappop(open_until)
        if t >= 0:
            arrivals += 1
        if len(open_until) >= slots:
            refused += t >= 0
            continue
        heapq.heappush(open_until, t + rng.choice(pool))
        if t >= 0:
            peak = max(peak, len(open_until))
    return LoadReplay(hours, arrivals, peak, refused)


@dataclass(frozen=True)
class StormCheck:
    changes_per_s: float
    model_per_change: float
    tools_per_change: float
    requests_per_s: float
    tpm: float
    calls_in_flight: float


def storm_check(fit: Fit,
                changes_per_s: float = STORM_CHANGES_PER_S) -> StormCheck:
    """Chapter 5's storm, with the loop the traces measured."""
    per = fit.steps_mean * fit.tries_per_step
    calls = changes_per_s * per
    return StormCheck(
        changes_per_s=changes_per_s, model_per_change=per,
        tools_per_change=fit.tools_per_task,
        requests_per_s=changes_per_s * (per + fit.tools_per_task),
        tpm=calls * fit.tokens_in * 60,
        calls_in_flight=calls * fit.call_mean_s)
