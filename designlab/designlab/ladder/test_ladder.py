"""Chapter 46 tests: the ladder, the clock, the rubric, calibration."""
from __future__ import annotations

import copy
import os
import subprocess
import sys
import unittest
from pathlib import Path

from bank.taxonomy import LEVELS as BANK_LEVELS
from designs import registry
from method.artifacts import CLOCK

from ladder import agree, clock, notes, prompts, rubric, scores
from ladder.levels import LEVELS, TIER_TOP, tier_for

ROOT = Path(__file__).resolve().parents[1]
STRONG = [f"A{i:02d}a" for i in range(1, 13)]
WEAK = [f"A{i:02d}b" for i in range(1, 13)]


class TestLadder(unittest.TestCase):
    def test_seven_levels_match_the_bank_codes(self):
        self.assertEqual(tuple(lv.code for lv in LEVELS), BANK_LEVELS)
        bars = [lv.bar for lv in LEVELS]
        self.assertEqual(bars, sorted(bars))

    def test_twelve_prompts_cover_every_level(self):
        self.assertEqual(len(prompts.PROMPTS), 12)
        for code, ids in prompts.by_level().items():
            self.assertTrue(ids, code)

    def test_reference_designs_exist(self):
        for p in prompts.PROMPTS.values():
            if p["design"]:
                self.assertIn(p["design"], registry.DESIGNS)

    def test_clock_folds_all_eight_slices_in_order(self):
        idx = [i for _, _, ix in clock.MARKS for i in ix]
        self.assertEqual(idx, list(range(len(CLOCK))))


class TestRubric(unittest.TestCase):
    def test_worked_answers_clear_and_close_sixty_gaps(self):
        gaps = 0
        for aid in STRONG:
            s = rubric.score(notes.load(aid))
            self.assertTrue(s.cleared, (aid, s.reasons))
            gaps += len(clock.closed(notes.load(aid)))
        self.assertEqual(gaps, 60)

    def test_other_answers_fall_below_their_level(self):
        for aid in WEAK:
            self.assertFalse(rubric.score(notes.load(aid)).cleared, aid)

    def test_no_estimate_scores_below_the_level(self):
        n = notes.without(notes.load("A08a"), "estimate")
        s = rubric.score(n)
        self.assertGreaterEqual(s.total, 10)       # over the bar
        self.assertFalse(s.cleared)
        self.assertIn("no estimate", s.reasons)

    def test_model_first_answer_misses_every_mark(self):
        n = notes.load("A03b")
        self.assertEqual(clock.marks_met(n), 0)
        self.assertGreaterEqual(notes.minutes_on(n, "model"), 25)

    def test_checker_does_not_read_right(self):
        n = notes.load("A01b")
        m = copy.deepcopy(n)
        for e in m["said"]:
            e.pop("right", None)
        self.assertEqual(rubric.score(n).row(), rubric.score(m).row())

    def test_component_rubric_ranks_the_list_first(self):
        allv = {a: rubric.score_v0(notes.load(a)) for a in STRONG + WEAK}
        top = max(allv, key=allv.get)
        self.assertEqual(top, "A09b")
        self.assertFalse(rubric.score(notes.load(top)).cleared)

    def test_register_a_level_seven_prompt(self):
        p = dict(prompts.PROMPTS["P12"], id="P99",
                 title="A partner's agent calls ours")
        prompts.register(p)
        try:
            self.assertIn("P99", prompts.by_level()["L7"])
            with self.assertRaises(ValueError):
                prompts.register(dict(p, id="P98", follow_ups=["one"]))
        finally:
            prompts.unregister("P99")
        self.assertEqual(len(prompts.PROMPTS), 12)

    def test_tiers(self):
        self.assertEqual(TIER_TOP["staff"], "L6")
        self.assertEqual(tier_for(["L1", "L2", "L3"]), "mid")
        self.assertEqual(tier_for(["L1", "L3", "L4"]), "below mid")


class TestCalibration(unittest.TestCase):
    def test_two_scorers_agree_on_141_of_168(self):
        d, h = scores.scorer("daniel"), scores.scorer("hannah")
        self.assertEqual(agree.exact(agree.cells(d, h)), (141, 168))

    def test_tradeoffs_did_not_move(self):
        d, h = scores.scorer("daniel"), scores.scorer("hannah")
        before, after = scores.split()
        self.assertEqual((len(before), len(after)), (16, 8))
        i = rubric.CRITERIA.index("tradeoffs")
        b = agree.exact(agree.cells(d, h, before, i))
        a = agree.exact(agree.cells(d, h, after, i))
        self.assertEqual(b[0] / b[1], a[0] / a[1])

    def test_kappa_bounds(self):
        self.assertEqual(agree.kappa([(1, 1), (2, 2), (0, 0)]), 1.0)
        self.assertLess(agree.kappa([(0, 2), (2, 0)]), 0)

    def test_model_scores_replay_offline(self):
        from ladder.live import replay
        rows, info = replay()
        self.assertEqual(info["model"], "claude-haiku-5-5")
        self.assertGreaterEqual(len(rows), 20)


class TestDemo(unittest.TestCase):
    def test_demo_runs_offline_and_fits(self):
        env = dict(os.environ, DESIGNLAB_OFFLINE="1")
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("RUN_LIVE", None)
        r = subprocess.run([sys.executable, "-m", "ladder.demo"],
                           cwd=ROOT, env=env, capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        long = [ln for ln in r.stdout.splitlines() if len(ln) > 70]
        self.assertEqual(long, [])


if __name__ == "__main__":
    unittest.main()
