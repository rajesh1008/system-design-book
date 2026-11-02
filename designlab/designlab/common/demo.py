"""Batch 0 foundation, offline: run ids, the trail, the spend meter.

    python3 -m common.demo

Seeded and clock-fixed, so the output is the same on every run. The
model call is replayed from a recorded fixture; no key is needed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .client import FixtureTransport, ModelClient
from .clock import FixedClock
from .ids import run_id
from .models import pins
from .rand import seeded
from .spend import SpendCapExceeded, SpendMeter
from .trail import TrailWriter, check_trail
from .text import emit

SEED = 2026
FIXTURES = Path(__file__).with_name("fixtures")


def main() -> None:
    clock = FixedClock("2026-01-05T09:00:00+00:00")
    rid = run_id("run", clock, seeded(SEED, "demo"))
    emit(f"run {rid}  seed={SEED}")

    emit("\nPinned models (common/models.toml)")
    for role, p in pins().items():
        emit(f"  {role:9} {p.id:27} in ${p.input_usd_per_mtok:5.2f}"
             f"  out ${p.output_usd_per_mtok:5.2f} /Mtok")

    emit("\nTrail: three entries, then one edited")
    trail = TrailWriter(clock=clock)
    trail.append({"event": "proposal", "itinerary": "LTG-4471902"})
    trail.append({"event": "permission", "permission_id": "PRM-20931",
                  "api_key": "pasted-by-mistake"})
    trail.append({"event": "effect", "key": "idem-3c1f"})
    emit(f"  lines={len(trail.lines)}  check={check_trail(trail.lines)}")
    stored = json.loads(trail.lines[1])["api_key"]
    emit(f"  line 2 api_key stored as {stored}")
    edited = list(trail.lines)
    edited[0] = edited[0].replace("4471902", "4471903")
    emit(f"  after edit: {check_trail(edited)[0]}")

    emit("\nSpend meter: a replayed call, then a cap of $0.0001")
    client = ModelClient("small", meter=SpendMeter(cap_usd=0.05),
                         transport=FixtureTransport(FIXTURES))
    r = client.complete("Reply with the word ok.", max_tokens=8)
    emit(f"  {r.model}: {r.text!r}  tokens {r.input_tokens}+"
         f"{r.output_tokens}  ${r.cost_usd:.6f}")
    tight = ModelClient("frontier", meter=SpendMeter(cap_usd=0.0001),
                        transport=FixtureTransport(FIXTURES))
    try:
        tight.complete("Summarize this itinerary. " * 40, max_tokens=512)
    except SpendCapExceeded as exc:
        emit("  refused before sending:")
        emit(f"  {exc}")


if __name__ == "__main__":
    main()
