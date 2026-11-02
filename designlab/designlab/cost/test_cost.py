"""Chapter 18 tests: the cost model and budget enforcement. Offline."""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

from common.text import too_long

from . import budget as B
from . import cache as C
from . import demo
from . import forecast as F
from . import levers as LV
from .unit import (APRIL, MAY, attribute, by_kind, ladder, month_cost,
                   sample)


class TestUnit(unittest.TestCase):
    def test_may_and_april_match_the_scoreboard(self):
        self.assertEqual(round(month_cost(MAY)["per_outcome"], 2), 1.84)
        self.assertEqual(round(month_cost(APRIL)["per_outcome"], 2),
                         2.95)

    def test_every_recorded_task_is_costed(self):
        self.assertEqual(len(sample()), 10_527)

    def test_ladder_rises_as_the_unit_gets_honest(self):
        values = [v for _n, v in ladder()]
        self.assertEqual(values[1:], sorted(values[1:]))
        self.assertLess(values[4], values[5])   # failed attempts count

    def test_tokens_are_a_small_part_of_the_outcome(self):
        c = month_cost(MAY)
        self.assertLess(c["lines"]["model tokens"] / c["total"], 0.05)

    def test_kinds_add_up_to_the_month(self):
        total = sum(sum(v["lines"].values()) for v in by_kind().values())
        self.assertAlmostEqual(total, month_cost(MAY)["total"], delta=1)

    def test_attribution_sums_to_the_cent(self):
        parts = attribute(595_000, {"a": 1.0, "b": 1.0, "c": 1.0})
        self.assertEqual(sum(parts.values()), 595_000)


class TestLevers(unittest.TestCase):
    def test_model_mix_moves_the_model_line_most(self):
        rows = LV.sensitivity()
        self.assertEqual(rows[0]["lever"], "model mix")
        self.assertEqual(rows[-1]["lever"], "retries")

    def test_handoffs_move_the_outcome_more_than_any_token_lever(self):
        rows = LV.sensitivity()
        widest = max(r["outcome_worse"] - r["outcome_better"]
                     for r in rows)
        h = dict(LV.handoff_lever())
        self.assertGreater(h[0.18] - h[0.06], 3 * widest)


class TestCache(unittest.TestCase):
    def test_semantic_cache_serves_other_customers(self):
        r = C.semantic(0.92)
        self.assertGreater(r["other_customer"], 0)
        self.assertGreater(r["wrong"], 0)

    def test_policy_only_cache_never_crosses_customers(self):
        self.assertEqual(C.policy_only()["other_customer"], 0)


class TestBudget(unittest.TestCase):
    def test_runaway_as_run_costs_46_dollars(self):
        r = B.replay_runaway()
        self.assertEqual(round(r.spent), 46)
        self.assertEqual(r.calls, 264)

    def test_failure_injection_no_budget_fails_the_budget_test(self):
        r = B.replay_runaway(loop_cap=False)
        self.assertTrue(B.check_runaway(r, B.Limits()))

    def test_enforcer_stops_the_runaway_under_budget(self):
        e = B.Enforcer()
        r = B.replay_runaway(e)
        self.assertEqual(B.check_runaway(r, e.limits), [])
        self.assertEqual(r.refused_wakes, 10)
        self.assertEqual(e.over(), [])

    def test_budget_survives_a_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "budget.json"
            e = B.Enforcer(B.Limits(task_usd=0.30), B.Store(path))
            rid = e.reserve("T1", "V1", "2026-05-01", 0.20)
            e.settle(rid, 0.20)
            again = B.Enforcer(B.Limits(task_usd=0.30), B.Store(path))
            with self.assertRaises(B.BudgetStop):
                again.reserve("T1", "V1", "2026-05-01", 0.20)

    def test_reservation_closes_the_race(self):
        self.assertGreater(B.race(reserve=False)["spent"], 1.00)
        self.assertLessEqual(B.race(reserve=True)["spent"], 1.00)

    def test_may_replay_has_no_run_over_budget(self):
        r = B.replay_month()
        self.assertEqual(r["over"], [])
        self.assertLess(r["max_task"], B.Limits().task_usd)

    def test_surge_stops_at_intake_not_over_budget(self):
        r = B.replay_month(day_scale={4: 3.0})
        self.assertGreater(r["stops"].get("intake", 0), 0)
        self.assertEqual(r["over"], [])


class TestForecast(unittest.TestCase):
    def test_june_inside_band_july_outside(self):
        rows = {r["month"]: r for r in F.forecast()}
        j = rows["June 2026"]
        self.assertTrue(j["low"] <= j["actual"] <= j["high"])
        self.assertGreater(rows["July 2026"]["actual"],
                           rows["July 2026"]["high"])


class TestDemo(unittest.TestCase):
    def test_output_fits_the_page_and_repeats(self):
        outs = []
        for _ in range(2):
            buf = io.StringIO()
            argv = sys.argv
            sys.argv = ["demo", "--part", "budget"]
            try:
                with contextlib.redirect_stdout(buf):
                    demo.main()
            finally:
                sys.argv = argv
            outs.append(buf.getvalue())
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(too_long(outs[0]), [])


if __name__ == "__main__":
    unittest.main()
