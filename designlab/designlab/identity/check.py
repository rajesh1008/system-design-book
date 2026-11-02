"""The trail check: three identities, a signature, a bound permission.

For every tool_call line: the customer, the agent configuration, and
the run are present; the signature over them, the permission, and the
argument digest verifies; and every allowed effect names a permission.
A line that fails names which part failed. Lines written by the gateway
before identity (Chapter 26) carry none of it and fail on the first.
"""
from __future__ import annotations

import json

from common.trail import check_trail

from .gate import line_sig

EFFECTS = {"rebook_ticket", "refund_ticket", "credit_issue",
           "voucher_issue", "customer_notify", "handoff_to_desk"}


def check(lines: list[str]) -> dict:
    out = {"lines": 0, "three_ids": 0, "signed": 0,
           "effects_allowed": 0, "effects_bound": 0,
           "refused_unknown": 0, "chain": check_trail(lines),
           "problems": []}
    for n, line in enumerate(lines, 1):
        e = json.loads(line)
        if e.get("event") != "tool_call":
            continue
        out["lines"] += 1
        ids = (e.get("user", ""), e.get("agent", ""), e.get("run", ""))
        if not all(ids):
            if e["verdict"] == "refused":
                out["refused_unknown"] += 1
            else:
                out["problems"].append(f"line {n}: allowed without "
                                       "three identities")
            continue
        out["three_ids"] += 1
        if e.get("sig") == line_sig(*ids, e.get("perm", ""),
                                    e["args_digest"]):
            out["signed"] += 1
        else:
            out["problems"].append(f"line {n}: signature")
        if e["verdict"] == "allowed" and e["tool"] in EFFECTS:
            out["effects_allowed"] += 1
            if e.get("perm"):
                out["effects_bound"] += 1
            else:
                out["problems"].append(f"line {n}: effect unbound")
    return out
