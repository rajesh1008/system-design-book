"""Tests for the Chapter 4 baseline. Offline, a few seconds."""
from __future__ import annotations

import unittest
from datetime import date

from corpus.ops import generate_ops
from baseline import (HONEST, VENDOR, Definition, automation_rate,
                      autonomy_share, baseline_row, count_changes,
                      decompose, dot_clock, metric_test, naive_count,
                      refund_error)

T = generate_ops(2026)


class TestVolume(unittest.TestCase):
    def test_contacts_are_not_changes(self):
        v = count_changes(T)
        self.assertEqual(naive_count(T)["units"], 14_000_000)
        self.assertEqual(v["changes"], 2_100_000)
        self.assertEqual(v["contacts_about_a_change"], 4_340_000)

    def test_mix_matches_chapter_one(self):
        g = count_changes(T)["by_group"]
        self.assertEqual(g, {"rebooking": 840_000, "cancellation": 520_000,
                             "refund": 480_000, "upgrade": 150_000,
                             "other": 110_000})

    def test_person_share(self):
        self.assertAlmostEqual(count_changes(T)["person_share"], 0.61)

    def test_logs_must_agree(self):
        broken = dict(T)
        broken["ops_changes"] = T["ops_changes"][1:]
        with self.assertRaises(ValueError):
            count_changes(broken)


class TestCost(unittest.TestCase):
    def test_paths(self):
        c = decompose(T)
        self.assertAlmostEqual(c["per_change"]["person"], 54.90, 2)
        self.assertAlmostEqual(c["per_change"]["self-service"], 11.40, 2)
        self.assertAlmostEqual(c["blended"], 37.94, 2)
        self.assertEqual(round(c["annual_usd"]), 79_663_500)

    def test_blend_is_recomposed(self):
        c = decompose(T)
        recomposed = sum(c["share"][p] * c["per_change"][p]
                         for p in c["share"])
        self.assertAlmostEqual(recomposed, c["blended"], 6)

    def test_rework_is_not_optional(self):
        self.assertLess(decompose(T, drop_rework=True)["blended"], 34.0)

    def test_labor_cross_check_within_two_percent(self):
        c = decompose(T)
        labor = c["pools"]["person"]["handle labor"]
        self.assertLess(abs(c["log_labor_per_change"] - labor) / labor,
                        0.02)

    def test_ten_percent_person_cost(self):
        self.assertAlmostEqual(decompose(T, 1.1)["blended"], 41.28, 2)


class TestErrors(unittest.TestCase):
    def test_matured_rate_is_point_eight(self):
        self.assertAlmostEqual(refund_error(T)["matured_rate"], 0.008, 4)

    def test_naive_rate_undercounts(self):
        e = refund_error(T)
        self.assertLess(e["naive_rate"], e["matured_rate"])

    def test_later_as_of_finds_more(self):
        early = refund_error(T)["found"]
        late = refund_error(T, as_of=date(2026, 2, 1))["found"]
        self.assertGreater(late, early)

    def test_email_only_carriers_worse(self):
        a = refund_error(T)["by_api"]
        self.assertGreater(a["email-only"], a["sync"])

    def test_dot_clock(self):
        d = dot_clock(T)
        self.assertEqual(d["self-service"][1], 0)
        self.assertGreater(d["person"][1], 0)


class TestAutonomy(unittest.TestCase):
    S = T["ops_pilot_sessions"]

    def test_vendor_and_honest(self):
        self.assertAlmostEqual(automation_rate(self.S, VENDOR), 0.54)
        self.assertAlmostEqual(automation_rate(self.S, HONEST), 0.09)

    def test_honest_definition_passes(self):
        self.assertEqual(metric_test(self.S, HONEST), {})

    def test_vendor_definition_fails(self):
        broken = metric_test(self.S, VENDOR)
        self.assertIn("counts a contact a person handled", broken)
        self.assertIn("counts an unverified change", broken)

    def test_abandons_fail_too(self):
        d = Definition("abandons", count_abandons=True)
        self.assertIn("counts an abandoned contact", metric_test(self.S, d))
        self.assertAlmostEqual(automation_rate(self.S, d), 0.30)

    def test_baseline_autonomy_is_zero(self):
        a = autonomy_share(T["ops_changes"])
        self.assertEqual(a["agent"], 0)
        self.assertEqual(a["assisted"], 0)


class TestScoreboard(unittest.TestCase):
    def test_row(self):
        row = {k: v for k, v, _ in baseline_row(T)}
        self.assertEqual(row["Cost per change"], "$37.94")
        self.assertEqual(row["Refund error"], "0.8%")
        self.assertEqual(row["Permission records"], "0")
        self.assertEqual(row["Person"], "61%")

    def test_every_number_has_an_owner(self):
        for _, _, who in baseline_row(T):
            self.assertTrue(who)


if __name__ == "__main__":
    unittest.main()
