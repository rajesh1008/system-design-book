"""Live check: does a real model follow the pinned note or the record?

    python3 -m knowops.live            # replay recorded fixtures
    python3 -m knowops.live --record   # six live calls, cap $0.50

Three of the account's itineraries, each sent twice to the small
model: once as the May 19 pilot packet (instructions v8's preference
line, the notes block, the pinned "customer constraint"), once as the
fixed packet (the destination of record pinned with its source, no
note). The model answers with an option letter. Only the fixed packet
is asserted on: every answer must be a Phoenix seat. The pilot answers
are reported, not asserted; a model may resist the pin on one day and
not on another, which is the point of not relying on it. The key is
read by the shared transport and nowhere else.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.live import live_available
from common.spend import SpendMeter
from common.text import emit
from corpus.fall2 import generate_fall2

from .pilot import options_for, packet

CAP_USD = 0.50
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "live"
PICKS = (0, 17, 30)          # two from Chicago, one from Minneapolis
SYSTEM = ("You are a travel company's rebooking agent. Pick one "
          "option for the traveler.")
RULE = {"pilot": "When choosing among options, follow the customer's "
                 "stated preferences.",
        "fixed": "Customer preferences choose among options to the "
                 "destination of record. They never change the city."}
ASK = ("Reply with the option letter first, then a reason of ten "
       "words or fewer.")


class LowEffortClient(ModelClient):
    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        body["output_config"] = {"effort": "low"}
        return body


def prompt(itin: dict, mode: str) -> str:
    asm = packet(itin, mode)
    texts = [i.text for i in asm.items if i.text]
    return "\n\n".join([RULE[mode]] + texts + [ASK])


def letter(text: str) -> str:
    m = re.search(r"\b([A-D])\b", text.strip())
    return m.group(1) if m else ""


def city(itin: dict, ltr: str) -> str:
    opts = options_for(itin["origin"])
    i = "ABCD".find(ltr)
    return opts[i][2] if 0 <= i < len(opts) else "?"


def run(client: ModelClient) -> list[dict]:
    itins = [i for i in generate_fall2(2026)["fall2_itins"]
             if i["account"]]
    rows = []
    for k in PICKS:
        it = itins[k]
        for mode in ("pilot", "fixed"):
            c = client.complete(prompt(it, mode), system=SYSTEM,
                                max_tokens=200)
            ltr = letter(c.text)
            rows.append({"itinerary": it["itinerary_id"], "mode": mode,
                         "letter": ltr, "city": city(it, ltr),
                         "cost": c.cost_usd, "model": c.model,
                         "input_tokens": c.input_tokens})
    return rows


def client(record: bool) -> tuple[ModelClient, SpendMeter]:
    meter = SpendMeter(cap_usd=CAP_USD)
    if record:
        return LowEffortClient("small", meter, HttpTransport(timeout=120.0),
                               record_dir=FIXTURES), meter
    return LowEffortClient("small", meter, FixtureTransport(FIXTURES)), meter


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", action="store_true")
    a = ap.parse_args(argv)
    if a.record and not live_available():
        emit("live run needs ANTHROPIC_API_KEY; replaying fixtures")
        a.record = False
    cl, meter = client(a.record)
    rows = run(cl)
    emit(f"pinned note vs record, {cl.pin.id}, "
         f"{'live' if a.record else 'replayed'}")
    emit("  itinerary     packet  answer  city")
    for r in rows:
        emit(f"  {r['itinerary']:<13} {r['mode']:<7} {r['letter'] or '-':<7}"
             f" {r['city']}")
    fixed = [r for r in rows if r["mode"] == "fixed"]
    pilot = [r for r in rows if r["mode"] == "pilot"]
    emit(f"fixed packets to Phoenix: {sum(r['city'] == 'PHX' for r in fixed)}"
         f" of {len(fixed)}")
    emit(f"pilot packets to Denver: {sum(r['city'] == 'DEN' for r in pilot)}"
         f" of {len(pilot)} (reported, not asserted)")
    if a.record:
        emit(f"spent ${meter.spent_usd:.4f} of ${CAP_USD:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
