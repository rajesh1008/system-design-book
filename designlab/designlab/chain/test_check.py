"""Gap finder and chain checker: unit tests (offline)."""
import unittest

from chain.check import DESIGNS, check_chain, find_gaps
from chain.incident import pilot_counts, report, thursday
from chain.lab import CANNED
from chain.states import run_rebooking
from corpus.generate import generate


def open_gaps(name):
    return [f["gap"] for f in find_gaps(DESIGNS[name])
            if f["status"] == "open"]


class TestGapFinder(unittest.TestCase):
    def test_pilot_has_two_open(self):
        self.assertEqual(open_gaps("pilot"), ["G2", "G4"])

    def test_chain_design_has_none(self):
        self.assertEqual(open_gaps("chain"), [])

    def test_second_settings(self):
        self.assertEqual(open_gaps("dispatch"), ["G2"])
        self.assertEqual(open_gaps("energy"), ["G4"])
        self.assertEqual(open_gaps("pharmacy"), ["G4"])

    def test_missing_record_opens_gap(self):
        d = dict(DESIGNS["chain"])
        d["business_result"] = {"writer": "scoreboard", "record": None}
        self.assertEqual([f["gap"] for f in find_gaps(d)
                          if f["status"] == "open"], ["G5"])


class TestChainCheck(unittest.TestCase):
    def test_clean_chain(self):
        recs, _ = run_rebooking(CANNED)
        self.assertEqual(check_chain(recs), [])

    def test_self_signed_verification_fails(self):
        recs, _ = run_rebooking(CANNED, forge="self_verify")
        self.assertTrue(any(p.startswith("G4") for p in check_chain(recs)))

    def test_self_granted_permission_fails(self):
        recs, _ = run_rebooking(CANNED, forge="self_permit")
        self.assertTrue(any(p.startswith("G2") for p in check_chain(recs)))

    def test_edit_after_the_fact_breaks_link(self):
        recs, _ = run_rebooking(CANNED)
        recs[2].body["max_fare_difference_usd"] = 9000.0
        self.assertIn("execution: link broken", check_chain(recs))

    def test_missing_state(self):
        recs, _ = run_rebooking(CANNED)
        self.assertIn("missing: business_result",
                      check_chain(recs[:5]))


class TestIncident(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = generate(seed=2026)

    def test_two_credits_three_seconds_apart(self):
        t = thursday(self.data)
        self.assertEqual([s["line_id"] for s in t["settlement"]],
                         ["SL-0000044", "SL-0000045"])
        self.assertIsNone(t["refunds"][0]["permission_id"])

    def test_every_agent_refund_after_chain_live_has_permission(self):
        c = pilot_counts(self.data)
        self.assertEqual(c["after"]["refunds"],
                         c["after"]["with_permission"])
        self.assertEqual(c["after"]["double_credit"], 0)
        self.assertEqual(c["before"]["double_credit"], 1)

    def test_report_fits(self):
        self.assertEqual([x for x in report() if len(x) > 70], [])


if __name__ == "__main__":
    unittest.main()
