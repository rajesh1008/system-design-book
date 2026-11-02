"""Check that every pinned model ID answers, cheaply (live; needs a key).

    python3 -m common.probe [--roles small,mid] [--record DIR]

One call per role: an eight-token reply to a six-word prompt. A pin
passes when the response names the same model ID that was requested.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .client import ModelClient
from .live import KEY_ENV, live_available
from .models import pins
from .spend import SpendMeter
from .text import emit

PROMPT = "Reply with the word ok."


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default=",".join(pins()))
    ap.add_argument("--record", type=Path, default=None)
    args = ap.parse_args(argv)
    if not live_available():
        emit(f"{KEY_ENV} not set; nothing to probe")
        return 0
    meter = SpendMeter(cap_usd=0.05)
    failed = 0
    emit(f"{'role':9} {'model id':27} {'echo':5} {'in':>4} {'out':>4}"
         f" {'usd':>9}")
    for role in args.roles.split(","):
        c = ModelClient(role, meter=meter, record_dir=args.record)
        r = c.complete(PROMPT, max_tokens=8)
        ok = not r.drifted
        failed += not ok
        emit(f"{role:9} {c.pin.id:27} {'same' if ok else 'DIFF':5}"
             f" {r.input_tokens:>4} {r.output_tokens:>4}"
             f" {r.cost_usd:>9.6f}")
    emit(f"calls={meter.calls}  spent=${meter.spent_usd:.6f}"
         f"  drifted={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
