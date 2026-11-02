"""A tour of the Lakeshore corpus v0: sizes, ratios, and the anchor.

    python3 -m corpus.demo
"""
from __future__ import annotations

from collections import Counter

from common.text import emit
from .generate import ANCHOR, TABLES, VERSION, generate, manifest

SEED = 2026


def main() -> None:
    t = generate(SEED)
    m = manifest(t, SEED, "v0")
    emit(f"Lakeshore corpus {VERSION}, seed {SEED}")
    emit(f"digest {m['digest'][:32]}")
    for name in TABLES:
        emit(f"  {name:17} {len(t[name]):>6,}")

    changes = t["changes"]
    handled = Counter(c["handled_by"] for c in changes)
    contacts = t["contacts"]
    emit("\nRatios (fixed by the style sheet)")
    emit(f"  changes / contacts      "
         f"{len(changes) / len(contacts):6.1%}")
    emit(f"  handled by a person     "
         f"{handled['person'] / len(changes):6.1%}")
    emit(f"  handled by the pilot    "
         f"{handled['agent'] / len(changes):6.1%}")
    refunds = t["refunds"]
    wrong = sum(1 for f in refunds if f["error"])
    emit(f"  refunds found wrong     {wrong / len(refunds):6.1%}"
         f"  ({wrong} of {len(refunds)})")

    emit("\nChange types")
    for kind, n in Counter(c["type"] for c in changes).most_common():
        emit(f"  {kind:24} {n:>5}")

    emit(f"\nThe anchor: {ANCHOR['itinerary']}")
    for line in t["settlement_lines"]:
        if line["itinerary_id"] == ANCHOR["itinerary"]:
            emit(f"  {line['credited_at']}  {line['credit_ref']}"
                 f"  ${line['amount_usd']:.2f}  {line['refund_id']}")
    emit("  (UTC; the first credit is 14:32:14 in Chicago)")
    pilot = [f for f in refunds if f["handled_by"] == "agent"]
    with_perm = sum(1 for f in pilot if f["permission_id"])
    emit(f"  pilot refunds {len(pilot)}, with a permission record"
         f" {with_perm}")
    emit("  (chain records begin December 15, 2025)")
    planted = sum(e["contains_instruction"] for e in t["hotel_emails"])
    emit(f"\nHotel emails carrying instruction-shaped text: {planted}")


if __name__ == "__main__":
    main()
