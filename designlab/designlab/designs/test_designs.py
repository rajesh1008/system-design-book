"""Tests for the worked designs, the expansion, and the linter. Offline."""
from __future__ import annotations

import copy
import io
import unittest
from contextlib import redirect_stdout

from common.text import too_long
from designs import (DESIGNS, RULES, derived_tier, expand, lint,
                     register, register_rule)
from designs import demo, registry
from designs.economics import month
from designs.lint import gap_status, gaps_closed, method_lint
from designs.patterns import table
from method.design import from_dict


def _spec(did: str) -> dict:
    return copy.deepcopy(DESIGNS[did])


class TestShipped(unittest.TestCase):
    def test_six_designs_in_order(self):
        self.assertEqual(tuple(DESIGNS)[:6], registry.ORDER)

    def test_every_design_lints_clean(self):
        for did in registry.ORDER:
            with self.subTest(design=did):
                self.assertEqual([f.line() for f in lint(DESIGNS[did])],
                                 [])

    def test_thirty_gaps_and_six_records(self):
        self.assertEqual(sum(gaps_closed(DESIGNS[d])
                             for d in registry.ORDER), 30)
        self.assertEqual(sum(1 for d in registry.ORDER
                             if DESIGNS[d].get("record")), 6)

    def test_expansion_is_a_method_design(self):
        for did in registry.ORDER:
            d = from_dict(expand(DESIGNS[did]))
            self.assertEqual(method_lint.lint(d), [])
            self.assertIn("reviewers_needed", d.values)

    def test_refunds_need_75_approvers_at_storm_hour(self):
        d = from_dict(expand(DESIGNS["lakeshore-refunds"]))
        self.assertAlmostEqual(d.values["reviewers_needed"], 74.6, 1)

    def test_exercise_files_are_not_registered(self):
        self.assertNotIn("retail-returns", DESIGNS)


class TestFaults(unittest.TestCase):
    def test_actor_verifies_fails(self):
        s = _spec("lakeshore-refunds")
        s["verifiers"][0]["reads"] = "execution log"
        rules = {f.rule for f in lint(s)}
        self.assertTrue({"GRM-2", "IND-1"} <= rules)
        self.assertFalse(gap_status(s)["G4"])

    def test_verifier_that_acts_fails(self):
        s = _spec("bank-payments")
        s["verifiers"][0]["acts"] = True
        rules = {f.rule for f in lint(s)}
        self.assertTrue({"GRM-2", "IND-1"} <= rules)

    def test_no_gate_fails_collections(self):
        s = _spec("lender-collections")
        s.pop("human_gate")
        found = lint(s)
        self.assertIn("HUM-1", {f.rule for f in found})
        self.assertFalse(gap_status(s, found)["G2"])

    def test_bank_limit_moves_the_tier(self):
        s = _spec("bank-payments")
        t = next(e for e in s["effects"] if e["name"] == "transfer")
        t["limit_usd"] = 2500
        self.assertEqual(derived_tier(t), "approve")
        self.assertEqual([f.rule for f in lint(s)], ["PRM-1"])
        t["tier"] = "approve"
        self.assertEqual(lint(s), [])

    def test_status_from_the_model_fails(self):
        s = _spec("telecom-care")
        s["customer"]["done"] = "model confidence"
        rules = {f.rule for f in lint(s)}
        self.assertTrue({"CUS-1", "CUS-2"} <= rules)

    def test_rule_in_the_prompt_fails(self):
        s = _spec("insurer-claims")
        s["obligations"][0]["plane"] = "prompt"
        self.assertEqual([f.rule for f in lint(s)], ["REG-1"])

    def test_summary_field_missing_fails(self):
        s = _spec("lakeshore-rebooking")
        s["human_gate"]["summary"].remove("deadline")
        self.assertEqual([f.rule for f in lint(s)], ["CUS-3"])

    def test_seventh_draft_fails_many_ways(self):
        s = registry.load_spec(registry.DATA / "_seventh.toml")
        rules = {f.rule for f in lint(s)}
        for r in ("IND-1", "PRM-1", "HUM-1", "CUS-2", "REG-1", "ECO-1",
                  "GRM-2"):
            self.assertIn(r, rules)


class TestLadder(unittest.TestCase):
    def test_rungs(self):
        e = {"limit_usd": 100, "ladder": [[100, "act"], [500, "approve"]]}
        self.assertEqual(derived_tier(e), "act")
        e["limit_usd"] = 101
        self.assertEqual(derived_tier(e), "approve")
        e["limit_usd"] = 501
        self.assertEqual(derived_tier(e), "suggest")
        self.assertIsNone(derived_tier({"limit_usd": 5}))


class TestExtensible(unittest.TestCase):
    def test_register_design_and_rule(self):
        s = _spec("telecom-care")
        s["design"]["id"] = "telecom-copy"
        self.assertEqual(register(s), "telecom-copy")
        n = len(RULES)
        register_rule("TST-1", lambda spec: [])
        try:
            self.assertIn("telecom-copy", DESIGNS)
            self.assertEqual(lint(DESIGNS["telecom-copy"]), [])
            self.assertEqual(len(RULES), n + 1)
        finally:
            RULES.pop()
            DESIGNS.pop("telecom-copy")


class TestEconomics(unittest.TestCase):
    def test_seven_lines_sum(self):
        for did in registry.ORDER:
            m = month(DESIGNS[did])
            self.assertEqual(len(m.lines), 7)
            self.assertAlmostEqual(sum(m.lines.values()), m.total)
            self.assertLess(m.per_outcome, m.person_cost)

    def test_rebooking_pays_back_first(self):
        order = sorted(registry.ORDER,
                       key=lambda d: month(DESIGNS[d]).payback_months)
        self.assertEqual(order[0], "lakeshore-rebooking")
        self.assertEqual(order[-1], "insurer-claims")


class TestPatterns(unittest.TestCase):
    def test_six_patterns_hold_everywhere(self):
        specs = {d: DESIGNS[d] for d in registry.ORDER}
        rows = table(specs)
        self.assertEqual(sum(1 for _n, r in rows if all(r)), 6)


class TestDemo(unittest.TestCase):
    def _run(self, *argv) -> tuple[int, str]:
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = demo.main(list(argv))
        return rc, buf.getvalue()

    def test_parts_fit_and_pass(self):
        rc, out = self._run()
        self.assertEqual(rc, 0)
        self.assertEqual(too_long(out), [])
        self.assertIn("gaps closed         30 of 30", out)

    def test_fault_runs_fail(self):
        for argv in (("--part", "lint", "--fault", "actor-verifies"),
                     ("--part", "lint", "--fault", "no-gate"),
                     ("--part", "lint", "--set",
                      "bank-payments:transfer.limit_usd=2500")):
            rc, out = self._run(*argv)
            self.assertEqual(rc, 1, argv)
            self.assertEqual(too_long(out), [])


if __name__ == "__main__":
    unittest.main()
