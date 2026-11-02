"""The Thursday refund, read from three systems (Chapter 2).

Reads the shared corpus (seed=2026) and lines up what each system says
about booking LTG-4471902: the vendor dashboard, the framework log, and
the processor's settlement file. Then counts pilot refunds before and
after the chain record went live on December 15, 2025.
"""
from __future__ import annotations

from collections import Counter

from corpus.generate import CHAIN_LIVE, generate

BOOKING = "LTG-4471902"

# The two tool views, as transcribed in the review on December 8, 2025.
DASHBOARD = [("14:32:07", "refund call", "status 200, 8.1 s")]
FRAMEWORK_LOG = [("14:32:07", "refund call", "attempt 1 of 3"),
                 ("14:32:15", "timeout", "after 8.0 s"),
                 ("14:32:16", "refund call", "attempt 2, 0.9 s")]


def thursday(data: dict) -> dict:
    refunds = [r for r in data["refunds"] if r["itinerary_id"] == BOOKING]
    lines = [s for s in data["settlement_lines"]
             if s["itinerary_id"] == BOOKING and s["kind"] == "credit"]
    tickets = [t for t in data["tickets"] if t["itinerary_id"] == BOOKING]
    return {"refunds": refunds, "settlement": lines, "tickets": tickets}


def pilot_counts(data: dict) -> dict:
    live = CHAIN_LIVE.strftime("%Y-%m-%dT%H:%M:%SZ")
    credits = Counter(s["refund_id"] for s in data["settlement_lines"]
                      if s["kind"] == "credit")
    out = {}
    agent = [r for r in data["refunds"] if r["handled_by"] == "agent"]
    for label, rows in (("before", [r for r in agent
                                    if r["issued_at"] < live]),
                        ("after", [r for r in agent
                                   if r["issued_at"] >= live])):
        out[label] = {
            "refunds": len(rows),
            "with_permission": sum(1 for r in rows
                                   if r["permission_id"]),
            "with_key": sum(1 for r in rows if r["idempotency_key"]),
            "double_credit": sum(1 for r in rows
                                 if credits[r["refund_id"]] > 1),
        }
    return out


def report(seed: int = 2026) -> list[str]:
    data = generate(seed=seed)
    t = thursday(data)
    out = [f"Booking {BOOKING}, Thursday, December 4, 2025 (CT)"]
    out.append("  vendor dashboard")
    out += [f"    {a}  {b:<12} {c}" for a, b, c in DASHBOARD]
    out.append("  framework log")
    out += [f"    {a}  {b:<12} {c}" for a, b, c in FRAMEWORK_LOG]
    out.append("  processor settlement file (UTC)")
    for s in t["settlement"]:
        out.append(f"    {s['credited_at'][11:19]}  {s['line_id']}  "
                   f"{s['credit_ref']}  ${s['amount_usd']:,.2f}")
    for r in t["refunds"]:
        out.append(f"  refund {r['refund_id']}  permission="
                   f"{r['permission_id'] or 'none'}  key="
                   f"{r['idempotency_key'] or 'none'}")
    for k in t["tickets"]:
        out.append(f"  ticket {k['ticket_id']}  {k['category']}  "
                   f"opened {k['opened_at'][:10]}")
    c = pilot_counts(data)
    out.append("Agent refunds around chain-live, December 15, 2025")
    for label in ("before", "after"):
        x = c[label]
        out.append(f"  {label:<6} refunds={x['refunds']}  "
                   f"permission={x['with_permission']}  "
                   f"double credits={x['double_credit']}")
    return out


if __name__ == "__main__":
    print("\n".join(report()))
