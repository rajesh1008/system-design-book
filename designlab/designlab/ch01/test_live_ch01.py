"""Live test for designlab v0: the small model writes the output.

One billed call, capped at 160 output tokens and $0.05 total. The model
only proposes; v0 classifies, asks the policy engine, executes against
the simulated network, and verifies with the reconciler. Skips cleanly
without ANTHROPIC_API_KEY.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from common.client import ModelClient
from common.live import KEY_ENV, skip_unless_live
from common.redact import find_secrets
from common.spend import SpendMeter

from . import demo
from .checker import audit
from .v0 import Network, V0Loop

METER = SpendMeter(cap_usd=0.05)


@skip_unless_live
class TestLiveV0(unittest.TestCase):
    def test_model_proposes_and_v0_does_the_rest(self):
        with tempfile.TemporaryDirectory() as d:
            c = ModelClient("small", meter=METER, record_dir=d)
            r = c.complete(demo.LIVE_PROMPT, system=demo.LIVE_SYSTEM,
                           max_tokens=160)
            saved = "".join(p.read_text() for p in Path(d).iterdir())
            self.assertEqual(find_secrets(saved, fixture=True), [])
            self.assertNotIn(os.environ[KEY_ENV], saved)
        t, world = demo.trail(), Network(slow_calls={1})
        rec = V0Loop(world, t).run("live-1", r.text)
        self.assertIsNotNone(rec, f"model reply was not an action")
        self.assertEqual(rec.proposal.itinerary, "LTG-4471902")
        self.assertAlmostEqual(rec.proposal.amount_usd, 412.60)
        self.assertEqual(len(world.effects), 1)
        a = audit(t.lines)
        self.assertEqual(sum(a["unanswered"].values()), 0)
        events = [json.loads(x)["event"] for x in t.lines]
        self.assertEqual(events[-1], "closed")
        print(f"\nlive reply: {r.text.strip()[:60]}")


def tearDownModule():
    if METER.calls:
        print(f"live spend: billed calls={METER.calls} "
              f"usd={METER.spent_usd:.6f}")


if __name__ == "__main__":
    unittest.main()
