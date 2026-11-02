"""Estimation: capacity = tokens x steps x retries, fitted to traces.

`fit_traces` reads the 90 days once and returns the numbers the rest
of the model uses. `estimate` turns a session rate into requests,
tokens, and things in flight.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean, pstdev

from corpus.traces import MODEL_TIMEOUT_S

from .queue import little
from .stats import Z95, lognormal_fit, pct


@dataclass(frozen=True)
class Fit:
    days: int
    sessions: int
    tasks: int
    steps_median: float         # exp(mu) of the lognormal fit
    steps_p95: float            # fitted 95th percentile
    steps_p95_seen: float       # read straight off the traces
    steps_mean: float
    steps_sigma: float
    tools_per_task: float       # tool calls, timeouts retried
    tries_per_step: float       # model calls that ran, per step
    asks_per_step: float        # requests sent, 429s included
    tokens_in: float            # per model call
    tokens_in_sd: float
    tokens_out: float
    follow_calls: float         # model calls per follow-up session
    task_share: float           # sessions that hold a task
    call_p95_s: float           # provider's view: accepted calls
    call_mean_s: float
    residence_s: float          # session open to close, mean
    mean_per_hour: float        # sessions an hour, all 90 days
    surge_ratio: float          # Monday 8 to 10 a.m. against mean


def fit_traces(sessions) -> Fit:
    tasks = [s for s in sessions if s.is_task]
    follows = [s for s in sessions if not s.is_task]
    n = [len(s.steps) for s in tasks]
    mu, sigma = lognormal_fit(n)
    steps = [x for s in sessions for x in s.steps]
    ran = sum(len(x.model_s) + x.error_s / MODEL_TIMEOUT_S for x in steps)
    asked = ran + sum(x.rejected_shared for x in steps)
    calls = [c for x in steps for c in x.model_s]
    tok = [x.tokens_in for x in steps]
    starts = [datetime.fromisoformat(s.started) for s in sessions]
    days = (max(starts).date() - min(starts).date()).days + 1
    surge = sum(1 for t in starts if t.weekday() == 0
                and t.hour in (8, 9))
    mondays = len({t.date() for t in starts if t.weekday() == 0})
    mean_h = len(sessions) / (days * 24)
    res = [s.knowledge_s + s.customer_s + s.idle_s + s.approval_s
           + sum(sum(x.model_s) + x.error_s + x.wait_shared
                 + sum(x.tool_s) + sum(x.gate_s) + x.trail_s + x.loop_s
                 for x in s.steps) for s in sessions]
    return Fit(
        days=days, sessions=len(sessions), tasks=len(tasks),
        steps_median=math.exp(mu),
        steps_p95=math.exp(mu + Z95 * sigma),
        steps_p95_seen=pct(n, 0.95), steps_mean=fmean(n),
        steps_sigma=sigma,
        tools_per_task=fmean(sum(len(x.tool_s) for x in s.steps)
                             for s in tasks),
        tries_per_step=ran / len(steps), asks_per_step=asked / len(steps),
        tokens_in=fmean(tok), tokens_in_sd=pstdev(tok),
        tokens_out=fmean(x.tokens_out for x in steps),
        follow_calls=fmean(len(s.steps) for s in follows),
        task_share=len(tasks) / len(sessions),
        call_p95_s=pct(calls, 0.95), call_mean_s=fmean(calls),
        residence_s=fmean(res), mean_per_hour=mean_h,
        surge_ratio=(surge / (2 * mondays)) / mean_h)


@dataclass(frozen=True)
class Estimate:
    sessions_per_s: float
    model_calls_per_s: float    # calls that run (tokens are paid)
    model_asks_per_s: float     # requests sent, rejections included
    tool_calls_per_s: float
    tokens_in_per_min: float
    tokens_out_per_min: float
    sessions_in_flight: float
    calls_in_flight: float
    tokens_per_task: float


def estimate(fit: Fit, sessions_per_hour: float,
             retry_scale: float = 1.0) -> Estimate:
    """Tokens x steps x retries, at a session rate.
    retry_scale multiplies the retries the traces show."""
    lam = sessions_per_hour / 3600
    tries = 1 + (fit.tries_per_step - 1) * retry_scale
    asks = 1 + (fit.asks_per_step - 1) * retry_scale
    steps = (fit.task_share * fit.steps_mean
             + (1 - fit.task_share) * fit.follow_calls)
    calls = lam * steps * tries
    tools = lam * fit.task_share * fit.tools_per_task
    return Estimate(
        sessions_per_s=lam, model_calls_per_s=calls,
        model_asks_per_s=lam * steps * asks, tool_calls_per_s=tools,
        tokens_in_per_min=calls * fit.tokens_in * 60,
        tokens_out_per_min=calls * fit.tokens_out * 60,
        sessions_in_flight=little(lam, fit.residence_s),
        calls_in_flight=little(calls, fit.call_mean_s),
        tokens_per_task=fit.steps_mean * tries * fit.tokens_in)
