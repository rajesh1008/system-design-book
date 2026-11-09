"""Chapter 35 tests: spans, conventions, cost per decision, the
completeness check and its injection, replay, alerts, sampling."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from decimal import Decimal

from common.redact import find_secrets
from common.text import too_long
from harness.manifest import apply_overrides
from harness.world import World, cases

from . import alerts, complete, cost, demo, questions, replay, sampling
from . import conventions as c
from .run import Gateway, fleet, harness, live
from .spans import Span, export, load

H = harness()
CASES = {x.cid: x for x in cases(1000)}


def one(cid="R-0002", **kw):
    gw = Gateway()
    return live(CASES[cid], H, World(), gw, **kw), gw


class TestSpans(unittest.TestCase):
    def test_names_follow_the_conventions(self):
        r, _ = one()
        names = {s.name for s in r.trace}
        self.assertIn("invoke_agent servicing", names)
        self.assertIn("chat claude-sonnet-5-5", names)
        self.assertIn("execute_tool refund_ticket", names)
        for s in r.trace:
            self.assertEqual(c.check_span(s), [], s.name)

    def test_check_span_flags_a_missing_attribute(self):
        r, _ = one()
        s = next(x for x in r.trace if x.name.startswith("chat "))
        del s.attrs[c.IN_TOKENS]
        self.assertTrue(any("input_tokens" in p for p in c.check_span(s)))

    def test_one_root_and_every_parent_exists(self):
        r, _ = one()
        ids = {s.span_id for s in r.trace}
        self.assertEqual(sum(s.parent_id is None for s in r.trace), 1)
        self.assertTrue(all(s.parent_id in ids for s in r.trace[1:]))

    def test_content_is_referenced_not_put_on_the_span(self):
        r, _ = one()
        for s in r.trace:
            blob = json.dumps(s.attrs)
            self.assertNotIn("LTG-", blob)
            if s.span_id in r.evidence:
                self.assertIn(c.IO_REF, s.attrs)

    def test_export_round_trip(self):
        r, _ = one()
        spans, ev = load(export(r.trace, r.evidence))
        self.assertEqual([s.to_json() for s in spans],
                         [s.to_json() for s in r.trace])
        self.assertEqual(len(ev), len(r.evidence))

    def test_runs_are_deterministic(self):
        a, _ = one()
        b, _ = one()
        self.assertEqual(export(a.trace, a.evidence),
                         export(b.trace, b.evidence))


class TestCost(unittest.TestCase):
    def test_every_model_span_is_priced(self):
        r, _ = one()
        chats = [s for s in r.trace if s.name.startswith("chat ")]
        self.assertTrue(chats)
        self.assertTrue(all(c.COST in s.attrs for s in chats))

    def test_decisions_add_up_to_the_run(self):
        fl = fleet(200)
        for r in fl.results:
            ds = cost.decisions(r.trace, r.evidence)
            self.assertEqual(sum(d["usd"] for d in ds), r.cost, r.cid)

    def test_stamp_writes_decision_cost_on_the_policy_span(self):
        r, _ = one()
        cost.stamp(r.trace, r.evidence)
        p = next(s for s in r.trace if s.name == "policy refund")
        self.assertEqual(Decimal(p.attrs[c.DECISION_COST]), r.cost)

    def test_cache_off_raises_cost_per_decision(self):
        on = cost.distribution(fleet(200).results)["all"]["p95"]
        off = cost.distribution(fleet(200, cache=False).results)
        self.assertGreater(off["all"]["p95"], 2 * on)


class TestComplete(unittest.TestCase):
    def test_normal_fleet_is_complete(self):
        rep = complete.fleet_report(fleet(300))
        self.assertEqual(rep["failed"], [])
        self.assertEqual(rep["steps"], rep["steps_traced"])
        self.assertEqual(rep["calls"], rep["calls_traced"])

    def test_injection_tool_call_outside_the_trace_fails(self):
        rep = complete.fleet_report(fleet(300, stray_every=100))
        self.assertEqual(len(rep["failed"]), 3)
        self.assertTrue(all("no span" in f.problems[0]
                            for f in rep["failed"]))

    def test_missing_policy_span_fails(self):
        r, gw = one(skip=("policy",))
        rep = complete.check(r.cid, r.trace, gw.trail.lines)
        self.assertIn("refund_ticket: no policy span permits it",
                      rep.problems)

    def test_missing_step_span_fails(self):
        r, gw = one(skip=("step",))
        rep = complete.check(r.cid, r.trace, gw.trail.lines,
                             conventions=False)
        self.assertEqual(rep.steps_traced, 0)
        self.assertFalse(rep.ok)

    def test_span_with_no_gateway_line_fails(self):
        r, gw = one()
        rep = complete.check(r.cid, r.trace, gw.trail.lines[:-1])
        self.assertTrue(any("no gateway line" in p for p in rep.problems))

    def test_orphan_span_fails(self):
        r, gw = one()
        r.trace.append(Span(r.trace[0].trace_id, "f" * 16, "0" * 16,
                            "step 99", attrs={c.STEP: 99}))
        rep = complete.check(r.cid, r.trace, gw.trail.lines)
        self.assertIn("orphan span step 99", rep.problems)


class TestQuestions(unittest.TestCase):
    def test_eleven_answers_with_the_policy_span(self):
        r, gw = one()
        a = questions.answers(r.trace, r.evidence, gw.trail.lines)
        self.assertEqual(len(a), 11)
        self.assertTrue(all(x is not None for _, x in a))

    def test_six_without_it(self):
        r, gw = one(skip=("policy",))
        a = questions.answers(r.trace, r.evidence, gw.trail.lines)
        self.assertEqual(sum(x is not None for _, x in a), 6)

    def test_a_tampered_trail_line_shows(self):
        r, gw = one()
        lines = [x.replace('"allowed"', '"refused"')
                 if '"refund_ticket"' in x else x for x in gw.trail.lines]
        a = dict(questions.answers(r.trace, r.evidence, lines))
        self.assertEqual(a["effect vs trail"], "MISMATCH")


class TestReplay(unittest.TestCase):
    def test_strict_replay_is_identical(self):
        fl = fleet(200)
        for r in fl.results:
            rp = replay.replay(CASES[r.cid], export(r.trace, r.evidence),
                               H)
            self.assertTrue(rp.diff.same, r.cid)
            self.assertEqual(rp.outcome, r.outcome)

    def test_replay_calls_nothing_live(self):
        r, _ = one()
        text = export(r.trace, r.evidence)
        short = "\n".join(x for x in text.splitlines()
                          if "execute_tool customer_notify" not in x)
        rp = replay.replay(CASES[r.cid], short + "\n", H)
        self.assertFalse(rp.diff.same)
        self.assertIn("strict replay called out", rp.error)

    def test_what_if_step_budget_diverges_at_the_stop(self):
        fl = fleet(200)
        h8 = apply_overrides(H, {"budgets.steps": 8})
        n = 0
        for r in fl.results:
            rp = replay.replay(CASES[r.cid], export(r.trace, r.evidence),
                               h8)
            if r.steps > 8:
                n += 1
                self.assertFalse(rp.diff.same)
                self.assertEqual(rp.diff.replay,
                                 "execute_tool handoff_to_desk")
            else:
                self.assertTrue(rp.diff.same, r.cid)
        self.assertGreater(n, 0)

    def test_what_if_policy_diverges_at_the_verdict(self):
        r, _ = one("R-0003")
        rp = replay.replay(CASES["R-0003"], export(r.trace, r.evidence),
                           H, "refunds-v4-draft")
        self.assertEqual(rp.diff.production, "policy refund")
        self.assertIn("policy.verdict", rp.diff.note)

    def test_bench_reports_zero_divergence(self):
        b = replay.bench(fleet(100), H)
        self.assertEqual(b["diverged"], 0)
        self.assertLess(b["p95_ms"], 1000)


class TestAlerts(unittest.TestCase):
    def test_normal_day_pages_nobody(self):
        m = alerts.metrics(fleet(300))
        self.assertFalse(any(f for _, f in alerts.evaluate(
            m, alerts.RULES)))

    def test_noise_rules_fire_on_a_normal_day(self):
        m = alerts.metrics(fleet(300))
        self.assertTrue(all(f for _, f in alerts.evaluate(
            m, alerts.NOISE)))

    def test_each_fault_pages_its_owner(self):
        cases_ = ((dict(refuse_reads=0.08), "reads refused > 5%"),
                  (dict(cache=False), "cost/decision p95 > $0.12"),
                  (dict(reconcile_faults=3), "effect not verified"),
                  (dict(stray_every=100), "trace incomplete"))
        for kw, name in cases_:
            fired = {r.name for r, f in alerts.evaluate(
                alerts.metrics(fleet(300, **kw)), alerts.RULES) if f}
            self.assertIn(name, fired, kw)

    def test_every_paging_rule_has_owner_and_action(self):
        for r in alerts.RULES:
            self.assertTrue(r.owner and r.action and r.pages)


class TestSampling(unittest.TestCase):
    def test_worked_problem_buffer(self):
        b = sampling.buffer_bytes(18_000, 1_100, 20, 45)
        self.assertEqual(b["live"], 396_000_000)
        self.assertEqual(b["pause"], 891_000_000)

    def test_effects_always_kept(self):
        k = sampling.decide({}, True, False, "x")
        self.assertEqual((k.keep, k.p), (True, 1.0))

    def test_wilson_contains_the_estimate(self):
        lo, hi = sampling.wilson(15, 50)
        self.assertLess(lo, 0.3)
        self.assertGreater(hi, 0.3)
        lo2, hi2 = sampling.wilson(15, 50, deff=2.0)
        self.assertLess(lo2, lo)


class TestDemo(unittest.TestCase):
    def test_every_part_fits_and_is_clean(self):
        for part, fn in demo.PARTS.items():
            if part in ("alerts", "version", "card", "cost", "sampling"):
                continue          # long parts run in run.sh
            buf = io.StringIO()
            with redirect_stdout(buf):
                fn()
            out = buf.getvalue()
            self.assertEqual(too_long(out), [], part)
            self.assertEqual(find_secrets(out), [], part)

    def test_conventions_are_pinned(self):
        self.assertIn("Development", c.PINNED)


if __name__ == "__main__":
    unittest.main()
