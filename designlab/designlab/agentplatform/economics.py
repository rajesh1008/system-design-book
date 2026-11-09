"""What a shared control plane costs against a control plane per use
case, and how to charge for it.

Monthly, in US dollars, at a loaded engineer cost of 16,000 a month.
Duplicated: each use case runs its own gateway, identity, policy,
evaluation harness, trace, and on-call share, 1.4 engineers plus 100
in tooling. Shared: a platform team of three engineers plus 7,000 in
infrastructure, and 2,000 a use case for onboarding and support.
Lakeshore figures are illustrative.
"""
from __future__ import annotations

ENGINEER = 16_000
DUP_FTE = {"gateway": 0.30, "identity": 0.15, "policy": 0.30,
           "evaluation": 0.25, "trace and dashboards": 0.20,
           "on-call share": 0.20}
DUP_TOOLING = 100
DUP_BUILD = 64_000          # one-time, per use case that builds its own
SHARED_FIXED = 3 * ENGINEER + 7_000
SHARED_PER = 2_000
AUGUST_CALLS = {"servicing": 2_412_000, "desk": 388_000,
                "loyalty": 41_000}


def duplicated(n: int) -> float:
    return n * (sum(DUP_FTE.values()) * ENGINEER + DUP_TOOLING)


def shared(n: int) -> float:
    return SHARED_FIXED + n * SHARED_PER


def break_even() -> float:
    per = duplicated(1)
    return SHARED_FIXED / (per - SHARED_PER)


def charges(calls: dict[str, int] = AUGUST_CALLS) -> list[tuple]:
    """(use case, by calls, equal split, marginal only, its own).

    By calls, the largest use case pays more than its own control
    plane would cost; by equal split, the smallest saves almost
    nothing. Marginal only means the fixed cost is funded centrally
    and each use case pays what it adds."""
    n = len(calls)
    total = shared(n)
    all_calls = sum(calls.values())
    own = duplicated(1)
    out = []
    for k, c in calls.items():
        by_calls = SHARED_PER + SHARED_FIXED * c / all_calls
        out.append((k, by_calls, total / n, SHARED_PER, own))
    return out

