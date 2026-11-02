"""Live test for Chapter 21: free and structured compaction prompts.

Six calls on the small model, cap $0.50. Skipped unless
ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1. The key is
read by the shared transport only; this file never touches it.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.live import skip_unless_live
from common.redact import find_secrets
from common.spend import SpendMeter
from context.live import LowEffortClient

from . import compaction


@skip_unless_live
class LiveCompaction(unittest.TestCase):
    def test_structured_prompt_survives_the_verifier(self):
        meter = SpendMeter(cap_usd=compaction.CAP_USD)
        with tempfile.TemporaryDirectory() as d:
            cl = LowEffortClient("small", meter,
                                 HttpTransport(timeout=120.0),
                                 record_dir=Path(d))
            rows = compaction.run(cl)
            for p in Path(d).glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [])
        struct = [r for r in rows if r["prompt"] == "structured"]
        self.assertEqual([r["findings"] for r in struct], [[], [], []])
        self.assertLess(meter.spent_usd, compaction.CAP_USD)


if __name__ == "__main__":
    unittest.main()
