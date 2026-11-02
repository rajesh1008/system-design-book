"""The assurance card: what Rachel Morgan's team reads at month end.
Each line names who measures it. Lakeshore figures are illustrative."""
from __future__ import annotations

from . import pack as P

OWNERS = {"findings": "Elena Vasquez", "pack": "Ben Carter",
          "sample": "Elena Vasquez", "dest": "Owen Fletcher",
          "anchors": "Rachel Morgan", "battery": "Owen Fletcher"}


def card(pk: dict, held: dict, finding_days: int, battery_effects: int,
         battery_total: int) -> list[tuple[str, str, str]]:
    a = pk["answers"]
    items = pk["sample"]["items"]
    ok = sum(1 for i in items if not P.check_sample(i, held))
    before = len(a["P5"]["proposed_elsewhere"])
    return [
        ("findings open June 30", f"1, closed in {finding_days} days",
         OWNERS["findings"]),
        ("refunds in the pack", f'{a["P1"]["count"]:,}', OWNERS["pack"]),
        ("sample chains complete", f"{ok} of {len(items)}",
         OWNERS["sample"]),
        ("to unregistered destinations", f"{before} proposed, 0 paid",
         OWNERS["dest"]),
        ("days anchored", f'{len(pk["anchors"])} of 30',
         OWNERS["anchors"]),
        ("battery effects", f"{battery_effects} of {battery_total}",
         OWNERS["battery"]),
    ]
