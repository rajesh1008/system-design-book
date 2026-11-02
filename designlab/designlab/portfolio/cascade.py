"""The cascade's verifier: reasons to escalate, from facts Lakeshore
controls.

A cascade is only as good as the check that decides to escalate. This
one never asks the small model how sure it is. It escalates when the
reply breaks its contract, when the model says it cannot tell, or when
the reply contradicts the booking record: an involuntary change type
with no carrier event on the booking, or a reference that is not the
customer's booking. What the verifier keeps, it keeps on evidence the
model did not produce.
"""
from __future__ import annotations

INVOLUNTARY = ("involuntary-rebook", "involuntary-refund")


def verify(step: str, obj: dict | None, contract_violations: list,
           facts: dict) -> list[str]:
    if obj is None or contract_violations:
        return ["contract"]
    reasons = []
    if step == "change-intent":
        if obj.get("change_type") == "unclear":
            reasons.append("unclear")
        if obj.get("change_type") in INVOLUNTARY \
                and not facts.get("carrier_event"):
            reasons.append("no-carrier-event")
        ref = facts.get("ref")
        if ref and obj.get("itinerary_ref") not in (None, ref):
            reasons.append("not-this-booking")
    if step == "booking-read" and obj.get("segment_id") is None:
        reasons.append("no-segment")
    return reasons
