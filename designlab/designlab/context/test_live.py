"""Live test for Chapter 21: early facts in long histories.

Six calls on the small model, about 4,000 to 85,000 tokens each, cap
$0.50. Skipped unless ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE
is not 1. The key is read by the shared transport only.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.live import skip_unless_live
from common.spend import SpendMeter

from . import live


@skip_unless_live
class LiveLongContext(unittest.TestCase):
    def test_every_history_stays_under_90k_and_is_scored(self):
        meter = SpendMeter(cap_usd=live.CAP_USD)
        with tempfile.TemporaryDirectory() as d:
            cl = live.LowEffortClient("small", meter,
                                      HttpTransport(timeout=120.0),
                                      record_dir=Path(d))
            rows = live.run(cl)
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertLess(r["input_tokens"], 90_000)
            self.assertEqual(r["model"], cl.pin.id)
        self.assertGreaterEqual(sum(r["ok"] for r in rows), 5)
        self.assertLess(meter.spent_usd, live.CAP_USD)


if __name__ == "__main__":
    unittest.main()
