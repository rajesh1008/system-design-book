"""Lakeshore's policy bundles, June 2026, as data.

Each rule names its policy version, so a decision can say which
version allowed or refused it, and a revoked version can be found in
every bundle that carries it. Lakeshore figures are illustrative.
"""
from __future__ import annotations

READS = ["booking_read", "fare_calc", "fare_rules_search",
         "flight_status", "offers_search", "notice_read", "doc_intake",
         "code_run"]
MONEY = ["refund_ticket", "voucher_issue", "credit_issue",
         "rebook_ticket"]

BASE = [
    {"id": "refund-limit", "policy": "refunds-v3", "type": "limit",
     "tools": ["refund_ticket"], "field": "amount_usd", "max": 1500.00,
     "route": "team lead desk"},
    {"id": "refund-approval", "policy": "refunds-v3",
     "type": "approval", "tools": ["refund_ticket"],
     "desk": "refund approver desk"},
    {"id": "rebook-limit", "policy": "rebook-v2", "type": "limit",
     "tools": ["rebook_ticket"], "field": "fare_difference_usd",
     "max": 250.00, "route": "agent desk"},
    {"id": "rebook-allow", "policy": "rebook-v2", "type": "allow",
     "tools": ["rebook_ticket"]},
    {"id": "voucher-limit", "policy": "vouchers-v1", "type": "limit",
     "tools": ["voucher_issue"], "field": "amount_usd", "max": 100.00,
     "route": "agent desk"},
    {"id": "voucher-budget", "policy": "vouchers-v1", "type": "budget",
     "tools": ["voucher_issue"], "field": "amount_usd"},
    {"id": "voucher-allow", "policy": "vouchers-v1", "type": "allow",
     "tools": ["voucher_issue"]},
    {"id": "credit-allow", "policy": "credits-v1", "type": "allow",
     "tools": ["credit_issue"]},
    {"id": "notify-allow", "policy": "notify-v1", "type": "allow",
     "tools": ["customer_notify"]},
]

SEQUENCE = [
    {"id": "refund-once-24h", "policy": "sequence-v1",
     "type": "count_within", "tools": ["refund_ticket"],
     "key": "ticket_number", "n": 1, "hours": 24,
     "route": "refund approver desk"},
    {"id": "rebook-twice-24h", "policy": "sequence-v1",
     "type": "count_within", "tools": ["rebook_ticket"],
     "key": "itinerary_id", "n": 2, "hours": 24, "route": "agent desk"},
    {"id": "no-voucher-after-refund", "policy": "sequence-v1",
     "type": "quiet_after", "event": "refund_ticket",
     "tools": ["voucher_issue"], "key": "itinerary_id",
     "minutes": 1440, "route": "agent desk"},
    {"id": "permission-15m", "policy": "sequence-v1",
     "type": "valid_for", "minutes": 15},
]

JUNE_22 = [
    {"id": "reads", "policy": "reads-v1", "type": "read",
     "tools": READS},
    {"id": "intake-escalate", "policy": "intake-v1",
     "type": "escalate_after", "event": "doc_intake", "tools": MONEY},
]

BUNDLES = {
    "pb-2026.06.08": BASE,
    "pb-2026.06.15": BASE + SEQUENCE,
    "pb-2026.06.22": JUNE_22 + BASE + SEQUENCE,
}
AUTHOR = "Owen Fletcher's team"
SIGNER = "Rachel Morgan"
