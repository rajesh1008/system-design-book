"""A/B with a fixed horizon, the cost of peeking, and why a bandit
does not belong on actions with effects.

A/B is for task types whose effects can be taken back or have none,
such as the wording of a notice. The sample size and the stop rule
are fixed before the first exposure and recorded in the bundle. Looking
at the result daily and stopping at the first significant day inflates
false alarms, which the A/A simulation shows. A bandit moves traffic
toward whichever arm its reward favors before the verdicts arrive; if
the reward is approval, it moves traffic toward the arm that approves
more, which is the arm that pays out wrongly more.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

import random
from math import sqrt
from statistics import NormalDist

Z = NormalDist()


def sample_size(p1: float, p2: float, alpha: float = 0.05,
                power: float = 0.80) -> int:
    """Runs per arm for a two-sided test of two proportions."""
    za = Z.inv_cdf(1 - alpha / 2)
    zb = Z.inv_cdf(power)
    pb = (p1 + p2) / 2
    num = (za * sqrt(2 * pb * (1 - pb))
           + zb * sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
    return int(num / (p1 - p2) ** 2) + 1


def ztest(x1: int, n1: int, x2: int, n2: int) -> float:
    """Two-sided p-value for a difference of two proportions."""
    p = (x1 + x2) / (n1 + n2)
    se = sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = (x1 / n1 - x2 / n2) / se
    return 2 * (1 - Z.cdf(abs(z)))


def fixed(p_a: float, p_b: float, n: int, seed: int = 821):
    rng = random.Random(seed)
    xa = sum(rng.random() < p_a for _ in range(n))
    xb = sum(rng.random() < p_b for _ in range(n))
    return xa, xb, ztest(xa, n, xb, n)


def peeking(p: float = 0.09, per_day: int = 600, days: int = 10,
            trials: int = 2000, seed: int = 7) -> tuple[float, float]:
    """A/A tests: the same arm twice. Returns the false-alarm rate when
    read once at the end, and when read daily and stopped at the first
    day with p < 0.05."""
    rng = random.Random(seed)
    end = peek = 0
    for _ in range(trials):
        xa = xb = n = 0
        hit = False
        for _ in range(days):
            for _ in range(per_day):
                xa += rng.random() < p
                xb += rng.random() < p
            n += per_day
            if ztest(xa, n, xb, n) < 0.05:
                hit = True
        end += ztest(xa, n, xb, n) < 0.05
        peek += hit
    return end / trials, peek / trials


def bandit(days: int = 30, per_day: int = 4000, approve=(0.80, 0.88),
           wrong=(0.01, 0.06), seed: int = 3):
    """Thompson sampling on approval as the reward. Returns per-day
    share sent to arm B and the cumulative wrong payouts by arm.
    Wrong payouts are discovered only after the window closes."""
    rng = random.Random(seed)
    a = [[1, 1], [1, 1]]          # Beta(successes, failures) per arm
    share, bad = [], [0, 0]
    for _ in range(days):
        sent_b = 0
        for _ in range(per_day):
            draws = [rng.betavariate(*a[0]), rng.betavariate(*a[1])]
            arm = 0 if draws[0] >= draws[1] else 1
            sent_b += arm
            ok = rng.random() < approve[arm]
            a[arm][0 if ok else 1] += 1
            if ok and rng.random() < wrong[arm] / approve[arm]:
                bad[arm] += 1
        share.append(sent_b / per_day)
    return share, bad
