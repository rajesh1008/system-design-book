"""Offline tests for the Chapter 5 method module. No network."""
from __future__ import annotations

import contextlib
import copy
import io
import unittest

from common.text import too_long

from . import demo
from .artifacts import ARTIFACTS, CHECKLIST, CLOCK, FIRST_TEN, QUESTIONS
from .design import FormulaError, evaluate, from_dict, load
from .lint import checklist, lint, lint_diagram


def rules(findings):
    return sorted(f.rule for f in findings)


class Artifacts(unittest.TestCase):
    def test_eight_artifacts_and_twelve_checks(self):
        self.assertEqual(len(ARTIFACTS), 8)
        self.assertEqual(len(CHECKLIST), 12)

    def test_first_ten_are_in_the_bank(self):
        self.assertEqual(len(FIRST_TEN), 10)
        self.assertTrue(set(FIRST_TEN) <= set(QUESTIONS))

    def test_clock_is_forty_five_minutes_without_gaps(self):
        self.assertEqual(CLOCK[0][0], 0)
        self.assertEqual(CLOCK[-1][1], 45)
        for (_, end, _), (start, _, _) in zip(CLOCK, CLOCK[1:]):
            self.assertEqual(end, start)


class Formulas(unittest.TestCase):
    def test_arithmetic(self):
        self.assertEqual(evaluate("a * (b + 1) / 2", {"a": 4, "b": 2}), 6)

    def test_unknown_name_and_calls_are_refused(self):
        with self.assertRaises(FormulaError):
            evaluate("a + c", {"a": 1})
        with self.assertRaises(FormulaError):
            evaluate("__import__('os')", {})


class Designs(unittest.TestCase):
    def test_v0_fails_exactly_three(self):
        found = lint(load("v0"))
        self.assertEqual(rules(found), ["DEC-1", "EST-1", "OWN-1"])
        failed = [r[0] for r in checklist(found) if not r[3]]
        self.assertEqual(failed, ["M1", "M2", "M3"])

    def test_v0_1_passes(self):
        self.assertEqual(lint(load("v0_1")), [])

    def test_demo_design_fails_most_checks(self):
        found = lint(load("demo-2025-10-06"))
        self.assertIn("GRM-1", rules(found))
        self.assertEqual(rules(found).count("ART-1"), 6)

    def test_estimate_values(self):
        v = load("v0_1").values
        self.assertAlmostEqual(v["avg_per_day"], 5753.4, places=1)
        self.assertAlmostEqual(v["peak_requests_per_s"], 18.65, places=2)
        self.assertAlmostEqual(v["reviewers_needed"], 67.1, places=1)

    def test_sensitivity_names_storm_days_first(self):
        top = load("v0_1").sensitivity("reviewers_needed")[0]
        self.assertEqual(top[0], "storm_days")

    def test_model_calls_do_not_move_reviewers(self):
        s = dict((n, (lo, hi)) for n, lo, hi in
                 load("v0_1").sensitivity("reviewers_needed"))
        lo, hi = s["calls_per_change"]
        self.assertAlmostEqual(lo, hi)


class Rules(unittest.TestCase):
    def setUp(self):
        self.raw = copy.deepcopy(load("v0_1").raw)

    def lint_raw(self, questions=None):
        return rules(lint(from_dict(self.raw), questions))

    def test_missing_assumption(self):
        self.raw["estimate"][1]["assumption"] = ""
        self.assertEqual(self.lint_raw(), ["EST-1"])

    def test_bad_formula(self):
        self.raw["estimate"][-1]["formula"] = "nobody / 2"
        self.assertEqual(self.lint_raw(), ["EST-2"])

    def test_owner_not_listed(self):
        self.raw["records"][0]["owner"] = "A Stranger"
        self.assertEqual(self.lint_raw(), ["OWN-1"])

    def test_rejected_option_needs_a_reason(self):
        self.raw["decisions"][0]["options"][1]["why_not"] = ""
        self.assertEqual(self.lint_raw(), ["DEC-2"])

    def test_record_needs_reversal(self):
        self.raw["records"][2]["reverse_if"] = ""
        self.assertEqual(self.lint_raw(), ["REC-1"])

    def test_dangling_link(self):
        self.raw["records"][0]["evidence"].append("est:nothing")
        self.assertEqual(self.lint_raw(), ["LINK-1"])

    def test_thin_deep_dive(self):
        self.raw["deep_dives"][1]["failure_modes"] = \
            self.raw["deep_dives"][1]["failure_modes"][:2]
        self.assertEqual(self.lint_raw(), ["DIVE-1"])

    def test_new_bank_question_fails_every_design(self):
        q = dict(QUESTIONS, K5="Who may change the prompt?")
        self.assertEqual(self.lint_raw(q), ["REQ-1"])

    def test_open_question_with_owner_passes(self):
        self.raw["requirements"]["K4"] = {"status": "open",
                                          "owner": "Dr. Hannah Clarke"}
        self.assertEqual(self.lint_raw(), [])

    def test_missing_gap_answer(self):
        del self.raw["gaps"]["G3"]
        self.assertEqual(self.lint_raw(), ["GAP-G3"])


class Grammar(unittest.TestCase):
    def setUp(self):
        self.dia = copy.deepcopy(load("v0_1").raw["diagram"])

    def test_ungated_effect(self):
        self.dia["edges"] = [e for e in self.dia["edges"]
                             if not (e["from"] == "policy"
                                     and e["to"] == "executor")]
        self.assertEqual(rules(lint_diagram(self.dia)), ["GRM-1"])

    def test_verifier_reading_the_actors_output(self):
        self.dia["edges"].append({"from": "trail", "to": "verifier",
                                  "kind": "data", "label": "log"})
        self.assertEqual(rules(lint_diagram(self.dia)), ["GRM-2"])

    def test_unknown_kind(self):
        self.dia["nodes"][1]["kind"] = "brain"
        self.assertEqual(rules(lint_diagram(self.dia)), ["GRM-3"])


class Demo(unittest.TestCase):
    def run_demo(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = demo.main(list(argv))
        return code, buf.getvalue()

    def test_demo_lines_fit_and_summary(self):
        code, out = self.run_demo()
        self.assertEqual(code, 0)
        self.assertEqual(too_long(out), [])
        self.assertTrue(out.rstrip().endswith(
            "v0 fails 3 checks, v0.1 passes"))

    def test_added_question(self):
        code, out = self.run_demo("--question", "K5=Who edits prompts?")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("new question fails"), 2)
        self.assertEqual(too_long(out), [])


if __name__ == "__main__":
    unittest.main()
