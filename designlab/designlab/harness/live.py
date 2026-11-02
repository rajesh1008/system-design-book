"""Chapter 25 live smoke: five refund cases through harness 1.1.0's
state machine, with the real small model in the intake state.

Intake calls the refund-reason Model Contract (Chapter 13) through the
production path, `models.runner.guarded_call`: contract check, one
repair, then a person. Every other state is code. The harness writes
its version, manifest hash and the model's echo into every trail line.
Reads ANTHROPIC_API_KEY from the environment through common.client and
never prints it. Five short calls; the meter caps spend at $0.02.

    python3 -m harness.live            # live, records fixtures
    python3 -m harness.live --replay   # offline, from fixtures/live
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from common.client import FixtureTransport, HttpTransport
from common.spend import SpendMeter
from common.text import emit
from common.trail import check_trail
from models.contract import load_contracts
from models.runner import client_for, golden_cases, guarded_call

from . import loops
from . import manifest as M
from .world import cases

FIXTURES = Path(__file__).parent / "fixtures" / "live"
GOLDEN = ("rr-01", "rr-02", "rr-05", "rr-07", "rr-10")
CAP_USD = 0.02


def run(transport=None, record: bool = True) -> list[str]:
    c = load_contracts()["refund-reason"]
    gold = {g["id"]: g for g in golden_cases(c)}
    meter = SpendMeter(cap_usd=CAP_USD)
    if transport is None:
        transport = HttpTransport()
    rec = FIXTURES if record else None
    if rec:
        rec.mkdir(parents=True, exist_ok=True)
    cl = client_for(c, transport, meter, rec)
    h = M.resolve(M.load("servicing-1.1.0"))
    hz = loops.Harness(h, trail=loops.new_trail(), echo=c.expect_echo)
    lines, base = [], cases(len(GOLDEN))
    for gid, case in zip(GOLDEN, base):
        g = gold[gid]
        case = replace(case, eligible=True, approve=True)
        seen = {}

        def intake(_case, g=g, seen=seen):
            out = guarded_call(c, cl, g["input"])
            seen["out"] = out
            if out.outcome == "dead-letter" or out.output["needs_person"]:
                return "unclear"
            return out.output["reason_code"]

        r = loops.state_machine(case, hz, intake=intake)
        got = seen["out"].output or {}
        want = g["expect"]["reason_code"]
        ok = "match" if got.get("reason_code") == want else "differs"
        lines.append(f"{gid} {str(got.get('reason_code')):20} {ok:7} "
                     f"{r.steps} step{'s' if r.steps > 1 else ''} {r.outcome}")
    tl = [json.loads(x) for x in hz.trail.lines]
    head = [f"harness {hz.version}  manifest {hz.hash}  "
            f"model {c.expect_echo}"]
    tail = [f"trail lines {len(tl)}, with manifest hash "
            f"{sum(e.get('manifest') == hz.hash for e in tl)}, links "
            f"{'intact' if not check_trail(hz.trail.lines) else 'broken'}",
            f"model calls {meter.calls}, spent ${meter.spent_usd:.4f} "
            f"(cap ${CAP_USD:.2f})"]
    return head + lines + tail


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--replay", action="store_true")
    a = p.parse_args(argv)
    if a.replay:
        out = run(FixtureTransport(FIXTURES), record=False)
    else:
        out = run()
    for line in out:
        emit(line)


if __name__ == "__main__":
    main()
