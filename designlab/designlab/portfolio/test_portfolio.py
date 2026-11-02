"""Offline tests for Chapter 15's portfolio. Every model answer is a
recorded call; a request with no recording is an error."""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from common.client import NoFixture
from common.redact import find_secrets
from common.spend import SpendMeter

from models.runner import ContractClient

from . import cases, demo
from .budget import BudgetClient, BudgetRefused, Candidate, cap, client
from .budget import contract_for
from .cascade import verify
from .check import run_check
from .pool import POOL, PoolTransport
from .steps import load_steps
from .table import build, gates

TR = PoolTransport()


class GoldenSets(unittest.TestCase):
    def test_golden_answers_match_the_reference_rules(self):
        steps = load_steps()
        want = {cid: cases.refund_rule(f) for cid, f in cases.GOLDEN_REFUND}
        for case in steps["refund-rule"].cases():
            self.assertEqual(case["expect"]["rule"], want[case["id"]])
        for case, (cid, opts, c) in zip(steps["offer-choice"].cases(),
                                        cases.GOLDEN_OFFER):
            self.assertEqual(case["expect"]["option_id"],
                             cases.choose_offer(opts, c))

    def test_router_tasks_are_fixed_by_their_seed(self):
        a, b = cases.router_tasks(), cases.router_tasks()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 40)
        self.assertTrue(all(len(t["steps"]) == 3 for t in a))


class Budgets(unittest.TestCase):
    def test_default_budget_sends_the_chapter_13_body(self):
        c = load_steps()["change-intent"].contract
        m = SpendMeter(cap_usd=1)
        ours = client(c, Candidate("frontier"), TR, m)
        theirs = ContractClient(c.role, meter=m, transport=TR)
        theirs.pin, theirs.schema = ours.pin, ours.schema
        args = (c.render({"message": "x"}), c.system, c.max_tokens, None)
        self.assertEqual(ours.request_body(*args),
                         theirs.request_body(*args))

    def test_effort_is_in_the_body_and_capped(self):
        c = contract_for(load_steps()["refund-rule"].contract,
                         Candidate("mid"))
        cl = client(c, Candidate.parse("mid@high"), TR, SpendMeter(1))
        self.assertIsInstance(cl, BudgetClient)
        body = cl.request_body("p", c.system, c.max_tokens, None)
        self.assertEqual(body["output_config"]["effort"], "high")
        self.assertEqual(cap(Candidate.parse("mid@high"), "high").effort,
                         "high")
        with self.assertRaises(BudgetRefused):
            cap(Candidate.parse("mid@max"), "high")

    def test_candidate_keeps_the_steps_limits(self):
        c = load_steps()["refund-rule"].contract
        s = contract_for(c, Candidate("small"))
        self.assertEqual(s.model_id, "claude-haiku-5-5")
        self.assertEqual((s.p95_latency_s, s.max_cost_usd),
                         (c.p95_latency_s, c.max_cost_usd))


class Verifier(unittest.TestCase):
    def test_reasons_come_from_the_record(self):
        ok = {"change_type": "involuntary-rebook",
              "itinerary_ref": "LTG-1"}
        self.assertEqual(verify("change-intent", ok, [],
                                {"carrier_event": True, "ref": "LTG-1"}),
                         [])
        self.assertIn("no-carrier-event",
                      verify("change-intent", ok, [], {"ref": "LTG-1"}))
        self.assertIn("not-this-booking",
                      verify("change-intent", ok, [],
                             {"carrier_event": True, "ref": "LTG-2"}))
        self.assertEqual(verify("change-intent", None, [], {}),
                         ["contract"])


class Routing(unittest.TestCase):
    def setUp(self):
        self.steps = load_steps()

    def test_gated_table(self):
        t = build(self.steps, TR, "gated")
        self.assertEqual(t["change-intent"].label, "small>frontier")
        self.assertEqual(t["booking-read"].label, "small")
        self.assertEqual(t["refund-rule"].label, "frontier")
        self.assertEqual(t["offer-choice"].label, "small")

    def test_floor_keeps_the_high_risk_step_off_small(self):
        gs = gates(self.steps, TR)
        small = next(g for g in gs["refund-rule"] if g.label == "small")
        self.assertTrue(small.ok)          # it passed the golden set
        t = build(self.steps, TR, "gated")
        self.assertNotEqual(t["refund-rule"].first.role, "small")

    def test_gated_check(self):
        t = build(self.steps, TR, "gated")
        r = run_check(cases.router_tasks(), self.steps, t, TR, "gated")
        self.assertEqual(r.high_risk_on(self.steps, "small"), 0)
        self.assertFalse(any(x.outcome == "wrong" for x in r.runs))
        self.assertEqual(r.success, 37)
        self.assertEqual(len(r.trail), 120)

    def test_cost_only_rule_fails_the_check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(demo.main(["check", "--rule", "cost-only"]), 1)
            self.assertEqual(demo.main(["check"]), 0)


class Records(unittest.TestCase):
    def test_an_unrecorded_request_is_an_error(self):
        with self.assertRaises(NoFixture):
            TR({"model": "claude-haiku-5-5", "messages": []})

    def test_recorded_calls_carry_no_secrets(self):
        files = sorted(POOL.glob("*.json"))
        self.assertGreater(len(files), 100)
        for p in files:
            self.assertEqual(find_secrets(p.read_text(), fixture=True), [])
            self.assertIn("x_latency_ms", json.loads(p.read_text())
                          ["response"])

    def test_demo_lines_fit_the_page(self):
        for cmd in (["steps"], ["gate"], ["budget"], ["table"],
                    ["cascade"], ["scorecard"]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(demo.main(cmd), 0)


if __name__ == "__main__":
    unittest.main()
