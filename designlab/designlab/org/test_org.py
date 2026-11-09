"""Tests for the team, the matrix, the checker and the rhythm. Offline."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import date

from common.text import too_long
from org import demo, rights
from org.card import CHARTER, card
from org.rhythm import FORUMS, stall_cost, unreviewed
from org.roles import JUNE_REQ, SEATS, available, seated
from org.skills import coverage, gaps, with_seat


class TestRoster(unittest.TestCase):
    def test_team_of_eleven(self):
        self.assertEqual(len(SEATS), 11)
        self.assertEqual(len(seated()), 9)
        self.assertEqual(len(seated(date(2026, 9, 14))), 11)

    def test_new_seat_cannot_decide_before_it_starts(self):
        why = available("agent systems architect", date(2026, 8, 31))
        self.assertIn("Sep 14", why)
        self.assertIsNone(available("agent systems architect",
                                    date(2026, 9, 14)))

    def test_unknown_name(self):
        self.assertEqual(available("Nobody", date(2026, 8, 31)),
                         "not on the roster")


class TestSkills(unittest.TestCase):
    def test_gaps_before_hires(self):
        self.assertEqual(gaps(), ["control", "evaluation"])

    def test_both_hires_close_the_gaps(self):
        self.assertEqual(gaps(date(2026, 9, 14)), [])

    def test_june_requisition_leaves_control_open(self):
        seats = with_seat(JUNE_REQ)
        self.assertEqual(gaps(date(2026, 9, 14), seats), ["control"])

    def test_lead_excluded_by_default(self):
        with_lead = coverage(count_lead=True)
        self.assertIn("Daniel Price", with_lead["control"])
        self.assertNotIn("Daniel Price", coverage()["control"])
        self.assertEqual(gaps(count_lead=True), [])


class TestMatrix(unittest.TestCase):
    def test_signed_matrix_one_owner_each(self):
        for d in rights.SIGNED:
            self.assertEqual(len(d.owners), 1, d.key)

    def test_signed_passes_six(self):
        res = rights.check_all()
        self.assertEqual(len(res), 6)
        self.assertTrue(all(not f for _, f in res))

    def test_august_4_fails_policy_change_only(self):
        res = rights.check_all(rights.AUG4, rights.SIGNERS["2026-08-04"])
        bad = {s.key: f for s, f in res if f}
        self.assertEqual(list(bad), ["policy-change"])
        self.assertEqual(bad["policy-change"][0].problem, "no owner")

    def test_draft_has_three_faults(self):
        res = rights.check_all(rights.DRAFT, rights.SIGNERS["2026-08-19"],
                               day=date(2026, 8, 19))
        problems = sorted(f.problem for _, fs in res for f in fs)
        self.assertEqual(len(problems), 3)
        self.assertTrue(any(p.startswith("two owners") for p in problems))
        self.assertTrue(any("Sep 14" in p for p in problems))

    def test_owner_without_key(self):
        f = rights.check(rights.SCENARIOS[0], signers=("Rachel Morgan",))
        self.assertEqual(f[0].problem,
                         "owner Marcus Bell holds no signing key")

    def test_author_team_cannot_certify(self):
        s = rights.SCENARIOS[1]
        s2 = rights.Scenario(s.key, s.title, s.day, "research engineer",
                             "research", s.needs)
        f = rights.check(s2)
        self.assertIn("on the author's team", f[0].problem)

    def test_gate_and_release_need_two_people(self):
        m = rights.reassign("release", "Hannah Clarke")
        res = rights.check_all(m)
        failed = [s.key for s, f in res if f]
        self.assertEqual(failed, ["model-change", "new-tool"])

    def test_without_risk(self):
        partners, gone = rights.without("Rachel Morgan")
        self.assertEqual(gone, {"Rachel Morgan", "Elena Vasquez"})
        res = rights.check_all(partners=partners)
        self.assertEqual(sum(1 for _, f in res if not f), 2)

    def test_seventh_scenario_needs_a_row(self):
        f = rights.check(rights.SEVENTH)
        self.assertEqual(f[0].problem, "not in the matrix")

    def test_urgent_without_deputy(self):
        m = rights._edit(rights.SIGNED, stop={"deputy": None})
        f = rights.check(rights.SCENARIOS[3], m)
        self.assertEqual(f[0].problem, "time-critical with no deputy")


class TestRhythmAndCard(unittest.TestCase):
    def test_every_decision_has_a_forum(self):
        self.assertEqual(unreviewed(), [])
        trimmed = tuple(f for f in FORUMS if f.name != "risk review")
        self.assertEqual(unreviewed(trimmed),
                         ["rules.refund", "rules.security",
                          "usecase.tier"])

    def test_stall(self):
        days, n, usd = stall_cost()
        self.assertEqual((days, n), (10, 1118))
        self.assertAlmostEqual(usd, 5131.62, places=2)

    def test_card(self):
        c = card()
        self.assertTrue(c["team size"].startswith("11 "))
        self.assertEqual(c["scenarios"], "6 of 6 pass")
        self.assertEqual(c["roles"], 6)

    def test_charter_first_line(self):
        self.assertIn("not the agent; it is the evidence", CHARTER[2])


class TestDemo(unittest.TestCase):
    def test_every_line_fits_70(self):
        runs = [[], ["--part", "gap", "--hire", "june"],
                ["--part", "gap", "--hire", "architect"],
                ["--part", "scenarios", "--matrix", "2026-08-19"],
                ["--part", "scenarios", "--fault", "no-owner"],
                ["--part", "scenarios", "--fault", "no-key"],
                ["--part", "scenarios", "--without", "Rachel Morgan"],
                ["--part", "scenarios", "--owner",
                 "release=Hannah Clarke"],
                ["--part", "scenarios", "--seventh"]]
        for argv in runs:
            buf = io.StringIO()
            with redirect_stdout(buf):
                demo.main(argv)
            self.assertEqual(too_long(buf.getvalue()), [], argv)


if __name__ == "__main__":
    unittest.main()
