"""Live contract test for Chapter 13: one real call, one cent at most.

Skipped unless ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1.
The key is read by the shared transport only; this file never touches it.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from common.client import HttpTransport
from common.live import skip_unless_live
from common.redact import find_secrets
from common.spend import SpendMeter

from .contract import check, load_contracts, parse_json
from .runner import client_for, golden_cases


@skip_unless_live
class LiveContract(unittest.TestCase):
    def test_pinned_snapshot_answers_and_meets_its_contract(self):
        c = load_contracts()["refund-reason"]
        case = golden_cases(c)[0]
        meter = SpendMeter(cap_usd=0.01)
        with tempfile.TemporaryDirectory() as d:
            cl = client_for(c, HttpTransport(), meter, Path(d))
            comp = cl.complete(c.render(case["input"]), system=c.system,
                               max_tokens=c.max_tokens)
            self.assertEqual(comp.model, c.expect_echo)
            self.assertEqual(check(c, comp, case["input"]), [])
            self.assertEqual(parse_json(comp.text)["reason_code"],
                             case["expect"]["reason_code"])
            for p in Path(d).glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [])
        self.assertLess(meter.spent_usd, 0.01)


if __name__ == "__main__":
    unittest.main()
