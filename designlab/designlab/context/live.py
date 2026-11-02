"""Live long-context sample: does the small model still find early facts?

    python3 -m context.live            # replay recorded fixtures
    python3 -m context.live --record   # six live calls, cap $0.50

Six seeded run histories, from about 4,000 to about 85,000 tokens, each
with its facts in the first lines: a customer constraint, a canceled
approval, and the pending approval with its amount and key. The model
is asked for the run's state. Every call goes through the shared client
and spend meter; the key is read by the transport and nowhere else.
Fixtures hold redacted request and response bodies only.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common.client import FixtureTransport, HttpTransport, ModelClient
from common.live import live_available
from common.spend import SpendMeter
from common.text import emit

from .transcript import QUESTION, facts, score, transcript

SEED = 21
LENGTHS = (4_000, 12_000, 24_000, 40_000, 60_000, 85_000)
CAP_USD = 0.50
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "live"
SYSTEM = ("You are a rebooking agent's state checker. Read the run "
          "history and report its state exactly as recorded.")


class LowEffortClient(ModelClient):
    """Sends effort "low" in output_config, so a reading task does not
    spend its output budget thinking. The effort is in the request
    body, so it is in the request hash and the fixture."""

    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        body["output_config"] = {"effort": "low"}
        return body


def run(client: ModelClient) -> list[dict]:
    rows = []
    for i, n in enumerate(LENGTHS):
        f = facts(SEED, i)
        prompt = transcript(f, SEED, i, n) + "\n\n" + QUESTION
        c = client.complete(prompt, system=SYSTEM, max_tokens=600)
        s = score(c.text, f)
        rows.append({"target": n, "input_tokens": c.input_tokens,
                     "score": s, "ok": all(s.values()),
                     "cost": c.cost_usd, "model": c.model})
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
    emit(f"long-context sample, {cl.pin.id}, "
         f"{'live' if a.record else 'replayed'}")
    emit("  target  input tok  approval amount key  constraint")
    for r in rows:
        s = r["score"]
        mark = lambda k: "yes" if s[k] else "NO"  # noqa: E731
        emit(f"  {r['target']:>6,}  {r['input_tokens']:>9,}  "
             f"{mark('approval'):<8} {mark('amount'):<6} "
             f"{mark('key'):<4} {mark('constraint')}")
    emit(f"all facts found in {sum(r['ok'] for r in rows)} of "
         f"{len(rows)} histories")
    if a.record:
        emit(f"spent ${meter.spent_usd:.4f} of ${CAP_USD:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
