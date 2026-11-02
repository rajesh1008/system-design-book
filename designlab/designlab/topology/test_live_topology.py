"""Live test for Chapter 27: three trap tasks through every design.

Thirty-three calls on the small model, cap $0.50. Skipped unless
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
from .eligibility import TASKS


@skip_unless_live
class LiveTopologies(unittest.TestCase):
    def test_three_traps_every_design(self):
        tasks = [t for t in TASKS if t.task_id in
                 ("E27-08", "E27-11", "E27-18")]
        meter = SpendMeter(cap_usd=live.CAP_USD)
        with tempfile.TemporaryDirectory() as d:
            cl = live.LowEffortClient("small", meter,
                                      HttpTransport(timeout=120.0),
                                      record_dir=Path(d))
            ts = live.run(cl, tasks)
        self.assertEqual(ts["single"].calls, 3)
        self.assertEqual(ts["orchestrator"].calls, 12)
        for d in live.DESIGNS:
            x = ts[d]
            self.assertEqual(x.correct + x.desk + x.wrong, 3, d)
        self.assertGreaterEqual(ts["single"].correct, 2)
        self.assertGreater(ts["debate"].tokens, ts["vote"].tokens)
        self.assertLess(meter.spent_usd, live.CAP_USD)


if __name__ == "__main__":
    unittest.main()
