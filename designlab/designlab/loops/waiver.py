"""The waiver watch, the second unattended loop (live June 25, 2026).

When a carrier publishes a waiver notice, the loop reads it, asks the
model once which booked itineraries it covers, and sends each of them
one templated update. Only the cost path is modeled here; the spec
in `spec.py` carries its seven properties. Lakeshore figures are
illustrative.
"""
from __future__ import annotations

from datetime import datetime

from cost.budget import BudgetStop
from gateway.core import Caller
from serving.prices import Bill

LOOP = "waiver-watch"
TOKEN = "wl-waiver-watch"
NOTICES = (("NTC-20655", "2026-06-25T14:10:00-05:00", 96),
           ("NTC-20661", "2026-06-26T06:40:00-05:00", 41),
           ("NTC-20670", "2026-06-28T19:25:00-05:00", 133))
MAP_IN, MAP_OUT, MAP_MAX = 14_000, 600, 1_024


def grant(fw) -> None:
    fw.w.callers[TOKEN] = Caller(
        "loop:waiver-watch",
        frozenset({"notice_read", "booking_read", "customer_notify"}),
        rate_per_s=5.0, burst=200)


def run_notice(fw, enf, control, nid: str, when: str, n: int) -> dict:
    fw.clock.set(datetime.fromisoformat(when))
    day = when[:10]
    r = fw.w.gateway.call(TOKEN, "status", "notice_read",
                          {"notice_id": nid})
    out = {"notice": nid, "read": r.ok, "notified": 0, "usd": 0.0}
    try:
        rid = enf.reserve(f"{nid}@{day}", LOOP, day,
                          Bill(uncached=MAP_IN, output=MAP_MAX).usd(
                              "mid"))
    except BudgetStop as e:
        out["stop"] = e.scope
        return out
    usd = Bill(uncached=MAP_IN, output=MAP_OUT).usd("mid")
    enf.settle(rid, usd)
    out["usd"] = usd
    for i in range(n):
        note = {"itinerary_id": f"LTG-{5400000 + 11 * i:07d}",
                "template": "update"}
        res = fw.w.gateway.call(TOKEN, "messaging", "customer_notify",
                                note, permission=control.permit(
                                    "customer_notify", note))
        out["notified"] += res.ok
    return out
