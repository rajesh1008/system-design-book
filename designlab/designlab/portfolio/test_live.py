"""Live test for Chapter 15: one real call to the small model on one
booking-read case, a fraction of a cent.

Skipped unless ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1.
The key is read by the shared transport only; this file never touches it.
"""
from __future__ import annotations

import unittest

from common.client import HttpTransport
from common.live import skip_unless_live
from common.spend import SpendMeter

from models.contract import check, parse_json

from .budget import Candidate, client, contract_for
from .steps import load_steps


@skip_unless_live
class LiveSmallStep(unittest.TestCase):
    def test_small_model_reads_a_booking_within_its_contract(self):
        step = load_steps()["booking-read"]
        case = step.cases()[0]
        c = contract_for(step.contract, Candidate("small"))
        meter = SpendMeter(cap_usd=0.01)
        cl = client(c, Candidate("small"), HttpTransport(), meter)
        comp = cl.complete(c.render(case["input"]), system=c.system,
                           max_tokens=c.max_tokens)
        self.assertEqual(comp.model, c.expect_echo)
        self.assertEqual(check(c, comp, case["input"]), [])
        self.assertEqual(parse_json(comp.text)["segment_id"],
                         case["expect"]["segment_id"])
        self.assertLess(meter.spent_usd, 0.01)


if __name__ == "__main__":
    unittest.main()
