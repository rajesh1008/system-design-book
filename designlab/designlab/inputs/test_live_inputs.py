"""Replay and live tests for the Chapter 23 eight-document lab.

The replay tests run offline from the recorded fixtures. The live test
is skipped unless ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is
not 1; it makes one call, well under one cent, and never touches the
key, which only the shared transport reads.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.live import skip_unless_live
from common.redact import find_secrets
from common.spend import SpendMeter

from . import live


class ReplayEight(unittest.TestCase):
    def test_contract_arm_holds_on_recorded_run(self):
        cl, _ = live.client(record=False)
        rows = live.run(cl)
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r["contract_keys_ok"] for r in rows))
        self.assertTrue(all(r["contract_flag"] for r in rows))
        for r in rows:
            if r["pilot_obeyed"]:
                self.assertTrue(r["pilot_refused"], r["id"])

    def test_fixtures_hold_no_secrets(self):
        for p in live.FIXTURES.glob("*.json"):
            self.assertEqual(find_secrets(p.read_text(), fixture=True),
                             [], p.name)


@skip_unless_live
class LiveOne(unittest.TestCase):
    def test_one_document_live_meets_schema(self):
        i, kind, text, _ = live.DOCS[0]
        meter = SpendMeter(cap_usd=0.01)
        with tempfile.TemporaryDirectory() as d:
            cl = live.LowEffortClient("small", meter, HttpTransport(),
                                      record_dir=Path(d))
            comp = cl.complete(live.contract_prompt(i, kind, text),
                               system=live.CONTRACT_SYSTEM,
                               max_tokens=1200)
            self.assertEqual(set(live.parse(comp.text)), live.SCHEMA)
            for p in Path(d).glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [])
        self.assertLess(meter.spent_usd, 0.01)
