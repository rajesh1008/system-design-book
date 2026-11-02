"""Live test for Chapter 24: the fixed packet keeps the city.

Six calls on the small model, short prompts, cap $0.50. Skipped unless
ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1. The key is
read by the shared transport only.
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
class LivePinnedNote(unittest.TestCase):
    def test_fixed_packet_keeps_phoenix(self):
        meter = SpendMeter(cap_usd=live.CAP_USD)
        with tempfile.TemporaryDirectory() as d:
            cl = live.LowEffortClient("small", meter,
                                      HttpTransport(timeout=120.0),
                                      record_dir=Path(d))
            rows = live.run(cl)
        self.assertEqual(len(rows), 6)
        for r in rows:
            self.assertEqual(r["model"], cl.pin.id)
        fixed = [r for r in rows if r["mode"] == "fixed"]
        self.assertTrue(all(r["city"] == "PHX" for r in fixed), fixed)
        self.assertLess(meter.spent_usd, live.CAP_USD)


if __name__ == "__main__":
    unittest.main()
