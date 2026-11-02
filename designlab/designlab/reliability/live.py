"""Chapter 37 live run: the golden set under an alias and a dated id.

Twelve schedule-change messages, four of them the combined retime and
renumber that broke on July 8, go to two models three times each: the
undated small alias and the dated snapshot. A case passes only if all
three trials return exactly its codes (pass^3), and the deterministic
code check reads every answer against the message text. Each reply's
model echo is compared with the pin. Seventy-two calls. Reads
ANTHROPIC_API_KEY through common.client and never prints it; the
meter caps spend at $0.10.

    python3 -m reliability.live            # live, records fixtures
    python3 -m reliability.live --replay   # offline, from fixtures/live
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.spend import SpendMeter
from common.text import emit

from .july8 import code_check

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures" / "live"
GOLDEN = HERE / "golden" / "schedule-change.jsonl"
CAP_USD = 0.10
K = 3
CODES = ("RETIME", "FLT_NUMBER_CHANGE", "CANCEL", "EQUIPMENT", "REROUTE")
SYSTEM = (
    "You code airline schedule-change messages for a travel agency. "
    "Codes: RETIME (a departure or arrival time changed), "
    "FLT_NUMBER_CHANGE (the flight now operates under another number), "
    "CANCEL, EQUIPMENT (aircraft type changed), REROUTE (routing or "
    "connection changed). A message can need more than one code. Reply "
    "with the codes only, comma separated, nothing else.")


def golden() -> list[dict]:
    return [json.loads(ln) for ln in GOLDEN.read_text().splitlines()
            if ln.strip()]


def parse(text: str) -> tuple:
    return tuple(sorted(set(re.findall("|".join(CODES), text.upper()))))


def run(transport=None, record: bool = True,
        roles=("small", "dated")) -> list[str]:
    meter = SpendMeter(cap_usd=CAP_USD)
    if transport is None:
        transport = HttpTransport()
    cases = golden()
    lines = [f"{len(cases)} cases, {sum(c['combined'] for c in cases)} "
             f"combined; k={K}"]
    for role in roles:
        cl = ModelClient(role, meter, transport,
                         record_dir=FIXTURES if record else None)
        passed = combined_passed = held = echoes_off = 0
        failed = []
        for c in cases:
            want = tuple(sorted(c["codes"]))
            ok = True
            for trial in range(1, K + 1):
                r = cl.complete(f"Trial {trial} of {K}.\nMessage: "
                                f"{c['message']}", SYSTEM, max_tokens=30)
                got = parse(r.text)
                echoes_off += r.drifted
                held += bool(code_check(c["message"], got))
                ok = ok and got == want
            passed += ok
            combined_passed += ok and c["combined"]
            if not ok:
                failed.append(c["id"])
        lines.append(f"{cl.pin.id}")
        lines.append(f"  pass^{K} {passed}/{len(cases)}; combined "
                     f"{combined_passed}/4; echo off pin {echoes_off}")
        lines.append(f"  code check would hold {held} of "
                     f"{len(cases) * K} answers")
        if failed:
            lines.append(f"  failed: {', '.join(failed)[:56]}")
    lines.append(f"{meter.calls} calls, ${meter.spent_usd:.4f}")
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replay", action="store_true")
    a = ap.parse_args(argv)
    t = FixtureTransport(FIXTURES) if a.replay else None
    for ln in run(t, record=not a.replay):
        emit(ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
