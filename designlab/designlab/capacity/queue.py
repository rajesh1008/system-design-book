"""Queueing at the model: Little's law, Kingman, Erlang C, and the
share of minutes a token rate limit is exceeded."""
from __future__ import annotations

import math
from statistics import NormalDist


def little(rate_per_s: float, residence_s: float) -> float:
    """L = lambda * W: items in the system on average."""
    return rate_per_s * residence_s


def kingman(rho: float, service_s: float, ca2: float = 1.0,
            cs2: float = 1.0) -> float:
    """Mean wait in queue, one server (Kingman's approximation).
    ca2 and cs2 are squared coefficients of variation of the gaps
    between arrivals and of service times; 1 and 1 is M/M/1."""
    if not 0 <= rho < 1:
        raise ValueError("utilization must be in [0, 1)")
    return rho / (1 - rho) * (ca2 + cs2) / 2 * service_s


def erlang_c(servers: int, offered: float) -> float:
    """Probability an arrival waits in an M/M/c queue."""
    if offered >= servers:
        return 1.0
    term, total = 1.0, 1.0
    for k in range(1, servers):
        term *= offered / k
        total += term
    term *= offered / servers
    top = term * servers / (servers - offered)
    return top / (total + top)


def slots_for(offered: float, max_wait_p: float = 0.01) -> int:
    """Fewest concurrent slots so at most max_wait_p of calls wait."""
    c = max(1, math.ceil(offered))
    while erlang_c(c, offered) > max_wait_p:
        c += 1
    return c


def minutes_over(limit: float, calls_per_min: float, mean_tok: float,
                 sd_tok: float) -> float:
    """Share of one-minute windows whose token demand exceeds a rate
    limit, for Poisson calls with random sizes (normal approx)."""
    mean = calls_per_min * mean_tok
    sd = math.sqrt(calls_per_min * (mean_tok ** 2 + sd_tok ** 2))
    return 1 - NormalDist(mean, sd).cdf(limit)
