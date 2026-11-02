"""Refund error, measured honestly when disputes arrive late.

A refund error is found when a customer disputes it through the bank,
weeks after the refund. Dividing errors found so far by all refunds
in the year undercounts the recent months. The honest rate uses only
cohorts old enough for disputes to have arrived (matured cohorts).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from corpus.ops import AS_OF, MATURE_DAYS, WEIGHTS


def refund_error(t: dict, as_of: date = AS_OF,
                 mature_days: int = MATURE_DAYS) -> dict:
    w = WEIGHTS["ops_refunds"]
    cut = (as_of - timedelta(days=mature_days)).isoformat()
    a = as_of.isoformat()
    rows = [x for x in t["ops_refunds"] if x["issued"] <= a]
    found = [x for x in rows if x["dispute_found"]
             and x["dispute_found"] <= a]
    matured = [x for x in rows if x["issued"] <= cut]
    m_found = [x for x in found if x["issued"] <= cut]
    by_month = defaultdict(lambda: [0, 0, 0])   # refunds, found, eventual
    for x in rows:
        m = x["issued"][:7]
        by_month[m][0] += 1
        if x["error"]:
            by_month[m][2] += 1
            if x["dispute_found"] <= a:
                by_month[m][1] += 1
    by_api = defaultdict(lambda: [0, 0])
    by_carrier = defaultdict(lambda: [0, 0])
    found_ids = {x["refund_id"] for x in m_found}
    for x in matured:
        by_api[x["refund_api"]][0] += 1
        by_carrier[x["carrier"]][0] += 1
        if x["refund_id"] in found_ids:
            by_api[x["refund_api"]][1] += 1
            by_carrier[x["carrier"]][1] += 1
    return {
        "refunds": len(rows) * w, "found": len(found) * w,
        "naive_rate": len(found) / len(rows),
        "matured_refunds": len(matured) * w,
        "matured_found": len(m_found) * w,
        "matured_rate": len(m_found) / len(matured),
        "cutoff": cut,
        "by_month": {m: tuple(v) for m, v in sorted(by_month.items())},
        "by_api": {k: v[1] / v[0] for k, v in by_api.items()},
        "by_carrier": {k: (v[1] / v[0], v[0] * w)
                       for k, v in by_carrier.items()},
        "kinds": _kinds(m_found),
    }


def _kinds(rows) -> dict:
    out: dict[str, int] = defaultdict(int)
    for x in rows:
        out[x["error"]] += WEIGHTS["ops_refunds"]
    return dict(out)


def dot_clock(t: dict, limit: int = 7) -> dict:
    """Involuntary refunds paid within `limit` business days of the
    carrier's confirmation, split by path."""
    out = {}
    for path in ("person", "self-service"):
        rows = [x for x in t["ops_refunds"]
                if x["type"] == "involuntary-refund" and x["path"] == path]
        late = sum(1 for x in rows if x["business_days_to_refund"] > limit)
        out[path] = (1 - late / len(rows), late * WEIGHTS["ops_refunds"])
    return out
