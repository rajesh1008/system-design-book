"""Lakeshore's operations tables for the baseline year (Chapter 4).

A separate generator from corpus v0, so the v0 digest does not move.
It covers the 12 months to September 30, 2025, plus the chatbot pilot
of July to September 2024. Each table is a row-level sample: one row
stands for WEIGHTS[table] real records, and the counts are exact at
that weight (exact sampling, not coin flips).

    from corpus.ops import generate_ops
    t = generate_ops(2026)        # dict of table name -> rows

Every record is invented. Carrier codes come from corpus v0.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta

from common.rand import DEFAULT_SEED, seeded
from .generate import Builder

OPS_VERSION = "ops-v1"
YEAR_START = date(2024, 10, 1)
YEAR_END = date(2025, 9, 30)
AS_OF = date(2025, 10, 14)          # the baseline review
PILOT_START = date(2024, 7, 1)
PILOT_END = date(2024, 9, 30)

# One row stands for this many real records.
WEIGHTS = {"ops_contacts": 200, "ops_changes": 200, "ops_refunds": 20,
           "ops_pilot_sessions": 10, "ops_cost_pools": 1,
           "ops_pilot_incidents": 1}
OPS_TABLES = tuple(WEIGHTS)

# Contacts by reason, as shares of 14 million.
CONTACT_REASONS = {
    "new-change": 0.15,           # each one opens a change
    "change-follow-up": 0.16,     # about a change already open
    "trip-status-info": 0.30,
    "booking-or-payment-q": 0.17,
    "new-booking-help": 0.12,
    "complaint-feedback": 0.06,
    "misrouted-other": 0.04,
}
CHANNELS = {"phone": 42, "chat": 20, "email": 14, "self-service": 24}

# type: (group, rows at 1:200, handled by a person, makes a refund)
CHANGE_MIX = {
    "voluntary-rebook":       ("rebooking", 1650, 1025, False),
    "involuntary-rebook":     ("rebooking", 1300, 1105, False),
    "schedule-change-accept": ("rebooking", 650, 360, False),
    "hotel-date-change":      ("rebooking", 600, 452, False),
    "cancel-for-credit":      ("cancellation", 1500, 600, False),
    "hotel-cancel":           ("cancellation", 1100, 572, True),
    "cancel-with-refund":     ("refund", 1050, 640, True),
    "involuntary-refund":     ("refund", 950, 700, True),
    "ancillary-refund":       ("refund", 400, 246, True),
    "upgrade":                ("upgrade", 750, 375, False),
    "name-correction":        ("other", 250, 190, False),
    "car-rental-change":      ("other", 300, 140, False),
}

# Month weights, October 2024 to September 2025 (winter storms, summer).
MONTH_WEIGHTS = [8.0, 7.6, 8.4, 9.2, 7.4, 8.0, 8.2, 8.6, 9.0, 9.4,
                 8.6, 7.6]

# Finance's cost pools for the year, US dollars (path, pool, category).
COST_POOLS = [
    ("person", "handle labor", "labor", 40_351_500),
    ("person", "repeat contacts", "labor", 10_760_400),
    ("person", "supervision, QA, training", "labor", 7_173_600),
    ("person", "telephony, CRM, GDS seats", "tooling", 6_148_800),
    ("person", "error rework", "rework", 5_892_600),
    ("self-service", "platform run", "tooling", 2_538_900),
    ("self-service", "carrier and GDS fees", "tooling", 2_375_100),
    ("self-service", "payment processing", "tooling", 1_310_400),
    ("self-service", "abandoned attempts", "rework", 1_556_100),
    ("self-service", "rework and disputes", "rework", 1_556_100),
]
LOADED_HOURLY_USD = 42.00

REFUND_ERROR_RATE = 0.008     # found in disputes, matured cohorts
MATURE_DAYS = 120             # the longest network clock we rely on
ERROR_KINDS = {"credit-not-processed": 45, "short-refund": 30,
               "duplicate-not-reversed": 15, "wrong-card": 10}
API_ERROR_WEIGHT = {"email-only": 2.0, "async-batch": 1.2, "sync": 0.7,
                    "hotel": 0.9}

# The chatbot pilot: outcomes as exact shares of sessions.
PILOT_OUTCOMES = {
    "bot-answered-verified": 0.09,
    "bot-answered-came-back": 0.06,
    "bot-handed-to-person": 0.39,
    "abandoned-in-bot": 0.21,
    "opted-out-to-person": 0.25,
}
PILOT_SESSIONS_ROWS = 4_800

PILOT_INCIDENTS = [
    {"incident_id": "PIL-1", "date": "2024-07-23",
     "what": "bot promised fee waivers the fare rules did not grant",
     "customers": 37, "cost_usd": 9_250, "found_after_days": 6,
     "found_by": "agents' calls, then transcripts",
     "chain_gap": "G1 output acted as a promise"},
    {"incident_id": "PIL-2", "date": "2024-08-08",
     "what": "bot said carrier rebookings were done; none checked",
     "customers": 64, "cost_usd": 21_700, "found_after_days": 2,
     "found_by": "airport desk calls",
     "chain_gap": "G4 outcome stated, never verified"},
    {"incident_id": "PIL-3", "date": "2024-08-30",
     "what": "hand-off loop sent customers back to the bot",
     "customers": 1_900, "cost_usd": 14_300, "found_after_days": 0,
     "found_by": "queue alarm, wait over 2 hours",
     "chain_gap": "metric counted hand-offs as automated"},
    {"incident_id": "PIL-4", "date": "2024-09-17",
     "what": "bot showed bookings it had no grant to read",
     "customers": 11, "cost_usd": 6_480, "found_after_days": 9,
     "found_by": "a customer's call to an agent",
     "chain_gap": "G2 no permission record"},
]


def months() -> list[str]:
    out, y, m = [], YEAR_START.year, YEAR_START.month
    for _ in range(12):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def apportion(total: int, weights: list[float]) -> list[int]:
    """Split total into integers proportional to weights, summing exactly."""
    s = sum(weights)
    raw = [total * w / s for w in weights]
    base = [int(x) for x in raw]
    order = sorted(range(len(raw)), key=lambda i: base[i] - raw[i])
    for i in order[:total - sum(base)]:
        base[i] += 1
    return base


def day_in(rng, month: str) -> date:
    y, m = map(int, month.split("-"))
    first = date(y, m, 1)
    nxt = date(y + (m == 12), 1 if m == 12 else m + 1, 1)
    return first + timedelta(days=rng.randrange((nxt - first).days))


def business_days(start: date, end: date) -> int:
    n, d = 0, start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def sub_business_days(end: date, n: int) -> date:
    d = end
    while n > 0:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


class OpsBuilder:
    def __init__(self, seed: int):
        self.seed = seed
        self.t: dict[str, list[dict]] = {n: [] for n in OPS_TABLES}
        ref = Builder(seed, "v0")
        ref.reference()
        self.carriers = ref.t["carriers"]

    def rng(self, label: str):
        return seeded(self.seed, OPS_VERSION, label)

    def contacts_and_changes(self) -> None:
        r = self.rng("contacts")
        n = 14_000_000 // WEIGHTS["ops_contacts"]
        reasons = []
        for reason, share in CONTACT_REASONS.items():
            reasons += [reason] * round(n * share)
        r.shuffle(reasons)
        per_month = apportion(n, MONTH_WEIGHTS)
        stamps = []
        for month, k in zip(months(), per_month):
            stamps += sorted(day_in(r, month) for _ in range(k))
        types = []
        for ctype, (_, rows, people, _) in CHANGE_MIX.items():
            types += [(ctype, True)] * people + \
                     [(ctype, False)] * (rows - people)
        r.shuffle(types)
        changes, contacts = [], []
        k = 0
        for i, (reason, day) in enumerate(zip(reasons, stamps)):
            row = {"contact_id": f"OC-{i + 1:06d}", "day": day.isoformat(),
                   "reason": reason, "change_id": None,
                   "source": "contact log (telephony and CRM)"}
            if reason == "new-change":
                ctype, person = types[k]
                k += 1
                cid = f"OCH-{k:05d}"
                row["change_id"] = cid
                row["channel"] = r.choices(
                    ["phone", "chat", "email"], [60, 28, 12])[0] \
                    if person else "self-service"
                group = CHANGE_MIX[ctype][0]
                changes.append({
                    "change_id": cid, "contact_id": row["contact_id"],
                    "day": row["day"], "type": ctype, "group": group,
                    "handled_by": "person" if person else "self-service",
                    "handle_minutes": round(r.lognormvariate(3.70, 0.42), 1)
                    if person else None,
                    "source": "booking system change log"})
            else:
                row["channel"] = r.choices(list(CHANNELS),
                                           list(CHANNELS.values()))[0]
            contacts.append(row)
        # Follow-ups point at a change opened earlier in the year.
        opened = []
        j = 0
        for row in contacts:
            if row["reason"] == "new-change":
                opened.append(row["change_id"])
            elif row["reason"] == "change-follow-up":
                if opened:
                    lo = max(0, len(opened) - 400)
                    row["change_id"] = opened[r.randrange(lo, len(opened))]
                else:
                    row["change_id"] = changes[j]["change_id"]
                    j += 1
        self.t["ops_contacts"] = contacts
        self.t["ops_changes"] = changes

    def refunds(self) -> None:
        r = self.rng("refunds")
        w = WEIGHTS["ops_refunds"]
        refund_types = {t: v[1] * WEIGHTS["ops_changes"] // w
                        for t, v in CHANGE_MIX.items() if v[3]}
        rows = []
        for ctype, n in refund_types.items():
            people = round(n * CHANGE_MIX[ctype][2] / CHANGE_MIX[ctype][1])
            paths = ["person"] * people + ["self-service"] * (n - people)
            r.shuffle(paths)
            per_month = apportion(n, MONTH_WEIGHTS)
            idx = 0
            for month, k in zip(months(), per_month):
                for _ in range(k):
                    hotel = ctype == "hotel-cancel"
                    car = None if hotel else r.choice(self.carriers)
                    amount = (r.uniform(20, 160) if ctype ==
                              "ancillary-refund" else
                              r.lognormvariate(5.75, 0.55))
                    rows.append({
                        "type": ctype, "path": paths[idx],
                        "issued": day_in(r, month).isoformat(),
                        "carrier": "hotel" if hotel else car["code"],
                        "refund_api": "hotel" if hotel
                        else car["refund_api"],
                        "network": r.choices(
                            ["visa", "mastercard", "amex", "other"],
                            [52, 30, 14, 4])[0],
                        "amount_usd": round(amount, 2)})
                    idx += 1
        rows.sort(key=lambda x: (x["issued"], x["type"], x["amount_usd"]))
        for i, row in enumerate(rows):
            row["refund_id"] = f"ORF-{i + 1:06d}"
            row["error"] = None
            row["dispute_found"] = None
            row["source"] = "payment ledger"
            # DOT prompt-refund clock: involuntary refunds on cards.
            if row["type"] == "involuntary-refund":
                paid = date.fromisoformat(row["issued"])
                if row["path"] == "self-service":
                    bd = r.choice([0, 1, 1, 2, 2, 3])
                else:
                    bd = r.choice([1, 2, 3, 3, 4, 5, 6]) \
                        if r.random() > 0.07 else r.randrange(8, 19)
                row["carrier_confirmed"] = sub_business_days(
                    paid, bd).isoformat()
                row["business_days_to_refund"] = bd
        # Errors: exactly 0.8% inside each stratum, weighted by how the
        # carrier takes refunds. Disputes surface 15 to 118 days later.
        cut = (AS_OF - timedelta(days=MATURE_DAYS)).isoformat()
        kinds = list(ERROR_KINDS)
        for stratum in (True, False):
            pool = [x for x in rows if (x["issued"] <= cut) == stratum]
            k = round(len(pool) * REFUND_ERROR_RATE)
            keyed = sorted(pool, key=lambda x: -r.random() ** (
                1 / API_ERROR_WEIGHT[x["refund_api"]]))
            for x in keyed[:k]:
                x["error"] = r.choices(kinds, list(ERROR_KINDS.values()))[0]
                lag = min(118, 15 + int(r.gammavariate(2.0, 18.0)))
                x["dispute_found"] = (date.fromisoformat(x["issued"])
                                      + timedelta(days=lag)).isoformat()
        self.t["ops_refunds"] = rows

    def pilot(self) -> None:
        r = self.rng("pilot")
        n = PILOT_SESSIONS_ROWS
        outcomes = []
        for name, share in PILOT_OUTCOMES.items():
            outcomes += [name] * round(n * share)
        r.shuffle(outcomes)
        span = (PILOT_END - PILOT_START).days + 1
        days = sorted(PILOT_START + timedelta(days=r.randrange(span))
                      for _ in range(n))
        rows = []
        for i, (o, d) in enumerate(zip(outcomes, days)):
            person = o in ("bot-handed-to-person", "opted-out-to-person")
            rows.append({
                "session_id": f"PS-{i + 1:05d}", "day": d.isoformat(),
                "outcome": o,
                "bot_engaged": o != "opted-out-to-person",
                "bot_said_resolved": o in ("bot-answered-verified",
                                           "bot-answered-came-back"),
                "routed_by_bot": o == "bot-handed-to-person",
                "reached_person": person,
                "abandoned": o == "abandoned-in-bot",
                "contact_within_7d": o == "bot-answered-came-back",
                "source": "vendor session export"})
        # Verified means a record the bot does not write agrees: the
        # contact log shows no contact from the customer, on any
        # channel, in the seven days after the bot closed the session.
        for row in rows:
            row["verified"] = (row["bot_said_resolved"]
                               and not row["contact_within_7d"]
                               and not row["reached_person"])
        self.t["ops_pilot_sessions"] = rows
        self.t["ops_pilot_incidents"] = [dict(x) for x in PILOT_INCIDENTS]

    def cost_pools(self) -> None:
        self.t["ops_cost_pools"] = [
            {"path": p, "pool": pool, "category": c, "annual_usd": usd,
             "source": "finance cost allocation, FY to Sep 30, 2025"}
            for p, pool, c, usd in COST_POOLS]

    def build(self) -> dict[str, list[dict]]:
        self.contacts_and_changes()
        self.refunds()
        self.pilot()
        self.cost_pools()
        return self.t


def generate_ops(seed: int = DEFAULT_SEED) -> dict[str, list[dict]]:
    return OpsBuilder(seed).build()


def ops_digest(tables: dict[str, list[dict]]) -> str:
    h = hashlib.sha256()
    for name in OPS_TABLES:
        for row in tables[name]:
            h.update(json.dumps(row, sort_keys=True,
                                separators=(",", ":")).encode() + b"\n")
    return h.hexdigest()
