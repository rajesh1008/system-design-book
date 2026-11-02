"""Tests for the Capacity Model (Chapter 10). Offline; seed 10."""
from __future__ import annotations

import contextlib
import io
import unittest

from common.text import too_long
from corpus.traces import digest, generate_traces

from . import budget as B
from . import demo
from .estimate import estimate, fit_traces
from .queue import erlang_c, kingman, little, minutes_over, slots_for
from .surge import load_replay, size_surge, storm_check

SEED = 10


class CapacityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.S = generate_traces(SEED)
        cls.f = fit_traces(cls.S)

    def test_traces_are_reproducible(self):
        self.assertEqual(digest(self.S), digest(generate_traces(SEED)))
        self.assertNotEqual(digest(self.S), digest(generate_traces(11)))

    def test_traces_use_central_time(self):
        first, last = self.S[0].started, self.S[-1].started
        self.assertTrue(first.startswith("2025-12-01"))
        self.assertTrue(first.endswith("-06:00"))
        self.assertTrue(last.startswith("2026-02-28"))

    def test_fit_matches_the_chapter(self):
        f = self.f
        self.assertAlmostEqual(f.steps_median, 7.4, delta=0.1)
        self.assertAlmostEqual(f.steps_p95, 19.1, delta=0.3)
        self.assertAlmostEqual(f.call_p95_s, 1.9, delta=0.05)
        self.assertAlmostEqual(f.surge_ratio, 2.6, delta=0.05)

    def test_estimate_is_tokens_times_steps_times_retries(self):
        e = estimate(self.f, 3600)
        steps = (self.f.task_share * self.f.steps_mean
                 + (1 - self.f.task_share) * self.f.follow_calls)
        self.assertAlmostEqual(
            e.model_calls_per_s, steps * self.f.tries_per_step)
        twice = estimate(self.f, 3600, retry_scale=2.0)
        self.assertGreater(twice.tokens_in_per_min, e.tokens_in_per_min)

    def test_queue_formulas(self):
        self.assertEqual(little(2.0, 3.0), 6.0)
        self.assertAlmostEqual(kingman(0.5, 1.0), 1.0)
        self.assertAlmostEqual(kingman(0.9, 1.0), 9.0)
        self.assertAlmostEqual(erlang_c(2, 1.0), 1 / 3)
        self.assertEqual(erlang_c(2, 2.0), 1.0)
        self.assertLessEqual(erlang_c(slots_for(2.5), 2.5), 0.01)
        self.assertGreater(minutes_over(100, 10, 9, 1),
                           minutes_over(120, 10, 9, 1))

    def test_per_task_p95_is_not_per_call(self):
        r = B.replay(self.S, B.AS_RUN)
        self.assertGreater(r.p95, 20 * self.f.call_p95_s)

    def test_designs_rank_and_march_meets_budget(self):
        a = B.replay(self.S, B.AS_RUN).p95
        o = B.replay(self.S, B.OWN).p95
        m = B.replay(self.S, B.MARCH)
        self.assertGreater(a, o)
        self.assertGreater(o, m.p95)
        self.assertLessEqual(m.p95, B.TASK_BUDGET_S)
        self.assertLess(m.handoff_share, 0.02)
        self.assertTrue(all(ok for *_, ok in B.check_budget(m)))

    def test_plane_p95s_do_not_add(self):
        m = B.replay(self.S, B.MARCH)
        self.assertGreater(sum(m.plane_p95.values()), m.p95)
        self.assertGreater(sum(B.PLANE_BUDGET.values()), B.TASK_BUDGET_S)

    def test_control_plane_costs_milliseconds(self):
        gates = [g for s in self.S for x in s.steps for g in x.gate_s]
        gates.sort()
        self.assertLess(gates[int(0.95 * len(gates))], 0.010)

    def test_doubled_retries_break_the_budget(self):
        from dataclasses import replace
        d = replace(B.MARCH, retry_scale=2.0)
        self.assertGreater(B.replay(self.S, d).p95, B.TASK_BUDGET_S)

    def test_task_prediction_lands_near_replay(self):
        actual = B.replay(self.S, B.AS_RUN).p95
        pred = B.predict(self.S, self.f, "task", seed=SEED)
        self.assertLess(abs(pred - actual) / actual, demo.TOLERANCE)

    def test_per_call_injection_is_caught(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = demo.main(["--seed", str(SEED), "--part", "predict",
                              "--inject", "per-call"])
        self.assertEqual(code, 1)
        self.assertIn("model check: FAIL", out.getvalue())

    def test_surge_sizing(self):
        p = size_surge(self.f)
        self.assertEqual(p.sessions, 420)
        self.assertLess(p.limit_util, 0.8)
        lr = load_replay(self.S, p.planned_per_s, p.sessions, seed=SEED)
        self.assertLess(lr.peak, p.sessions)
        self.assertEqual(lr.refused, 0)

    def test_storm_stays_below_thirty_requests(self):
        st = storm_check(self.f)
        self.assertGreater(st.requests_per_s, 18.6)
        self.assertLess(st.requests_per_s, 30)

    def test_demo_fits_the_page(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = demo.main(["--seed", str(SEED)])
        self.assertEqual(code, 0)
        self.assertEqual(too_long(out.getvalue()), [])

    def test_loop_that_ran_twelve_steps(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = demo.main(["--seed", str(SEED),
                              "--session", "S018387"])
        text = out.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("steps 12; needed 7", text)
        self.assertIn("as run: 38.4 s", text)
        self.assertIn("March design: 18.7 s", text)
        self.assertEqual(too_long(text), [])


if __name__ == "__main__":
    unittest.main()
