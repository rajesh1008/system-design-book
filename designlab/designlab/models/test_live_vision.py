"""Live image test for Chapter 23: one call, under one cent.

Skipped unless ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.live import skip_unless_live
from common.redact import find_secrets
from common.spend import SpendMeter

from .vision import IMAGE, VisionClient, parse


@skip_unless_live
class LiveVision(unittest.TestCase):
    def test_boarding_pass_read_live(self):
        meter = SpendMeter(cap_usd=0.01)
        with tempfile.TemporaryDirectory() as d:
            cl = VisionClient("small", meter, HttpTransport(timeout=120.0),
                              record_dir=Path(d))
            out = parse(cl.read_image(IMAGE.read_bytes()).text)
            self.assertEqual(out["fields"]["locator"], "HN8C2V")
            self.assertNotIn("business", str(out["fields"]))
            for p in Path(d).glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [])
        self.assertLess(meter.spent_usd, 0.01)
