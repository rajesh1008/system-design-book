"""Chapter 46 live contract test: one question from the pinned model.

Runs only with RUN_LIVE=1 and ANTHROPIC_API_KEY set (and
DESIGNLAB_OFFLINE not 1). Records nothing; spends under one cent.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.redact import find_secrets
from common.spend import SpendMeter

from models import interviewer


@unittest.skipUnless(interviewer.live_allowed(),
                     "RUN_LIVE=1 and ANTHROPIC_API_KEY needed")
class LiveInterviewer(unittest.TestCase):
    def test_pinned_model_asks_one_question(self):
        meter = SpendMeter(cap_usd=0.01)
        with tempfile.TemporaryDirectory() as d:
            cl = interviewer.LowEffortClient(
                "small", meter, HttpTransport(), record_dir=Path(d))
            a = interviewer.ask(cl, "Design a refund agent.", 30, "G3",
                                "agent loop, refund tool")
            self.assertEqual(a.model, "claude-haiku-5-5")
            self.assertEqual(a.problems, [])
            for p in Path(d).glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [])
        self.assertLess(meter.spent_usd, 0.01)


if __name__ == "__main__":
    unittest.main()
