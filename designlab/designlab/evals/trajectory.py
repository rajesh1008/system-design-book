"""Trajectory matching: exact on effects, tolerant on reads.

An effect, or a step that asks for one, must appear in the expected
order and nowhere else. Reads may come in another order and a few
extra reads are allowed, as long as every read an effect depends on
happened before that effect. That answers the fair objection that a
fixed tool sequence punishes agents for finding another valid path:
the path is free where it changes nothing, and fixed where it does.
"""
from __future__ import annotations

from collections import Counter

EFFECTS = ("propose", "refund_ticket", "customer_notify", "rebook_ticket",
           "credit_issue", "voucher_issue", "handoff_to_desk")
MAX_EXTRA = 2


def match(expected, actual, max_extra: int = MAX_EXTRA) -> tuple[str, str]:
    """('exact' | 'tolerated' | 'mismatch', why)."""
    expected, actual = list(expected), list(actual)
    if actual == expected:
        return "exact", ""
    eff_e = [c for c in expected if c in EFFECTS]
    eff_a = [c for c in actual if c in EFFECTS]
    if eff_a != eff_e:
        return "mismatch", f"effects {'>'.join(eff_a) or 'none'}"
    missing = Counter(expected) - Counter(actual)
    if missing:
        return "mismatch", f"missing {', '.join(sorted(missing))}"
    extra = Counter(actual) - Counter(expected)
    if sum(extra.values()) > max_extra:
        return "mismatch", f"{sum(extra.values())} extra reads"
    # every read an effect depends on comes before that effect
    for i, step in enumerate(expected):
        if step not in EFFECTS:
            continue
        need = Counter(c for c in expected[:i] if c not in EFFECTS)
        k = eff_e[:eff_e.index(step) + 1].count(step)
        pos = [j for j, c in enumerate(actual) if c == step][k - 1]
        have = Counter(c for c in actual[:pos] if c not in EFFECTS)
        if need - have:
            return "mismatch", f"{step} before {', '.join(need - have)}"
    return "tolerated", "reads differ"
