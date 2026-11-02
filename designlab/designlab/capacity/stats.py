"""Small statistics helpers: percentiles and a lognormal fit."""
from __future__ import annotations

import math
from statistics import NormalDist, fmean, pstdev

Z95 = NormalDist().inv_cdf(0.95)        # 1.645


def pct(xs, p: float) -> float:
    """Percentile with linear interpolation; p in 0..1."""
    s = sorted(xs)
    if not s:
        raise ValueError("no data")
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def lognormal_fit(xs) -> tuple[float, float]:
    """Return (mu, sigma) of log(x): median is exp(mu)."""
    logs = [math.log(x) for x in xs]
    return fmean(logs), pstdev(logs)


def lognormal_pct(mu: float, sigma: float, p: float) -> float:
    return math.exp(mu + NormalDist().inv_cdf(p) * sigma)
