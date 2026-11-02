"""Chapter 2 lab: one rebooking through six states, then break it.

    python3 -m chain.lab            # offline, canned model output
    python3 -m chain.lab --gaps     # also run the gap finder
"""
from __future__ import annotations

import argparse
import json

from common.clock import FixedClock
from common.trail import TrailWriter, check_trail

from .check import DESIGNS, SHORT, check_chain, find_gaps, summary
from .states import Reservations, run_rebooking

CANNED = ('I can move you to the earlier flight. {"action": "rebook", '
          '"itinerary": "LTG-4471902", "from_flight": "FLT-000001", '
          '"to_flight": "FLT-009001", "reason": "original moved 11 h"}')

SHOW = {
    "output": lambda b: f"text_sha={b['text_sha']}",
    "proposal": lambda b: f"{b['from_flight']}->{b['to_flight']} "
                          f"diff=${b['fare_difference_usd']:.2f}",
    "permission": lambda b: f"{b['permission_id']} {b['policy_version']}"
                            f" bound={b['bound_to']}",
    "execution": lambda b: f"attempts={len(b['attempts'])} "
                           f"{b['reported']} {b['ticket']}",
    "verified_outcome": lambda b: f"{b['verdict']} "
                                  f"tickets={b['tickets_for_key']}",
    "business_result": lambda b: f"{b['counts_as']} "
                                 f"${b['cost_usd']:.2f}",
}


def show(recs) -> list[str]:
    return [f"  {SHORT[r.state]:<11}{r.writer:<16}{SHOW[r.state](r.body)}"
            for r in recs]


def to_trail(recs) -> list[str]:
    trail = TrailWriter(clock=FixedClock(
        start="2025-12-18T15:02:11+00:00", step_seconds=1))
    for r in recs:
        trail.append({"state": r.state, "writer": r.writer,
                      "ref": r.ref, "prev": r.prev})
    return trail.lines


def main(gaps: bool = False, text: str = CANNED) -> list[str]:
    out = ["One rebooking, LTG-4471902, ORD to BOS"]
    recs, refusal = run_rebooking(text, Reservations(slow_calls={1}))
    out += show(recs)
    if refusal:
        out.append(f"  refused at {refusal[0]}: {'; '.join(refusal[1])}")
        return out
    lines = to_trail(recs)
    probs = check_chain(recs)
    out.append(f"  chain check: {len(probs)} problems, trail lines="
               f"{len(lines)}, trail check={len(check_trail(lines))}")
    for forge in ("self_verify", "self_permit"):
        bad, _ = run_rebooking(text, Reservations(slow_calls={1}),
                               forge=forge)
        out.append(f"Forged: {forge}")
        out += [f"  {p}" for p in check_chain(bad)]
    tampered, _ = run_rebooking(text, Reservations(slow_calls={1}))
    tampered[2].body["max_fare_difference_usd"] = 900.0
    out.append("Edited after the fact: permission limit")
    out += [f"  {p}" for p in check_chain(tampered)]
    if gaps:
        out.append("Gap finder")
        for name, design in DESIGNS.items():
            found = find_gaps(design)
            opened = [f"{f['gap']} ({f['why']})" for f in found
                      if f["status"] == "open"]
            out.append(f"  {name:<9} {summary(found)}")
            out += [f"            {o}" for o in opened]
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--gaps", action="store_true")
    ap.add_argument("--json", action="store_true",
                    help="print the six records as JSON")
    a = ap.parse_args()
    if a.json:
        recs, _ = run_rebooking(CANNED, Reservations(slow_calls={1}))
        for r in recs:
            print(json.dumps(r.as_dict(), indent=1))
    else:
        print("\n".join(main(gaps=a.gaps)))
