"""Chapter 34 tests: golden tasks, trajectories, the judge, pass^k,
online scoring, the improvement loop, and the Release Gate."""
from __future__ import annotations

import unittest
from dataclasses import replace

from harness import manifest as M

from . import agent as A
from . import gate as GT
from . import golden as G
from . import harvest as H
from . import judge as J
from . import online as O
from . import passk as P
from .score import score
from .trajectory import match

TASKS = G.build()
TOOLS = G.REFUND_TOOLS


class GoldenTests(unittest.TestCase):
    def test_counts_and_ids(self):
        self.assertEqual(len(TASKS), 640)
        self.assertEqual(G.by_class(TASKS)["refund_eligible"], 160)
        self.assertEqual(len({t.tid for t in TASKS}), 640)
        self.assertEqual(len(G.build(G.MARCH)), 560)

    def test_every_task_names_four_things(self):
        for t in TASKS:
            self.assertTrue(t.outcome and t.tools)
            self.assertEqual(t.forbidden, G.FORBIDDEN)
            if t.outcome == "refunded":
                self.assertEqual(t.effects[0][2], t.card)

    def test_deterministic(self):
        self.assertEqual(G.build()[100], TASKS[100])


class TrajectoryTests(unittest.TestCase):
    def test_exact_and_tolerated(self):
        self.assertEqual(match(TOOLS, TOOLS)[0], "exact")
        extra = ["booking_read", "fare_rules_search", *TOOLS[1:]]
        self.assertEqual(match(TOOLS, extra)[0], "tolerated")
        swap = ["fare_calc", "booking_read", *TOOLS[2:]]
        self.assertEqual(match(TOOLS, swap)[0], "tolerated")

    def test_effects_are_exact(self):
        two = [*TOOLS[:4], "refund_ticket", TOOLS[4]]
        self.assertEqual(match(TOOLS, two)[0], "mismatch")
        early = ["booking_read", "propose", "fare_calc", *TOOLS[3:]]
        self.assertEqual(match(TOOLS, early),
                         ("mismatch", "propose before fare_calc"))

    def test_extra_read_limit(self):
        many = ["booking_read"] + ["fare_rules_search"] * 3 + list(TOOLS[1:])
        self.assertEqual(match(TOOLS, many)[0], "mismatch")


class ScoreTests(unittest.TestCase):
    def test_final_answer_misses_wrong_card(self):
        rel = GT.JUNE[3]
        bad = [score(t, A.run(t, rel, 0)) for t in TASKS]
        wrong = [s for s in bad if not s.passed]
        self.assertEqual(len(wrong), 5)
        self.assertTrue(all(s.final_only for s in wrong))
        self.assertTrue(all("refund_other_card" in s.forbidden
                            for s in wrong))

    def test_clean_release_passes(self):
        for t in TASKS[:200]:
            self.assertTrue(score(t, A.run(t, GT.JUNE[8], 0)).passed, t.tid)


class JudgeTests(unittest.TestCase):
    def test_calibration_meets_bar(self):
        cal = GT.calibration()
        self.assertEqual(cal.n, 300)
        self.assertAlmostEqual(cal.kappa, 0.81, places=2)
        self.assertTrue(cal.valid_for(J.OfflineJudge()))

    def test_self_labels_refused(self):
        j = J.OfflineJudge()
        with self.assertRaises(J.NotCalibrated):
            GT.calibration(j, labels=j.id)

    def test_pin_change_invalidates(self):
        cal = GT.calibration()
        self.assertFalse(cal.valid_for(J.OfflineJudge(pin="small@new")))

    def test_kappa(self):
        self.assertAlmostEqual(J.kappa([1, 1, 0, 0], [1, 1, 0, 0]), 1.0)
        self.assertAlmostEqual(J.kappa([1, 0, 1, 0], [1, 1, 0, 0]), 0.0)


class PassKTests(unittest.TestCase):
    def test_estimates(self):
        self.assertAlmostEqual(P.pass_at_k(8, 7, 3), 1.0)
        self.assertAlmostEqual(P.pass_hat_k(8, 7, 3), 0.625)
        self.assertAlmostEqual(P.pass_hat_k(8, 8, 8), 1.0)
        self.assertAlmostEqual(P.pass_at_k(8, 0, 3), 0.0)
        rows = P.table([8, 4], 8, ks=[1])
        self.assertAlmostEqual(rows[0][1], 0.75)


class GateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate, cls.res = GT.run_june()

    def test_two_of_nine_blocked(self):
        blocked = [r.rel.rid for r in self.res if not r.passed]
        self.assertEqual(blocked, ["R-0609", "R-0617"])

    def test_reasons(self):
        r9, r17 = self.res[3], self.res[5]
        self.assertEqual(r9.forbidden, {"refund_other_card": 15})
        self.assertEqual(len(r9.regressions), 5)
        self.assertEqual(len(r17.regressions), 12)
        self.assertFalse(r17.forbidden)

    def test_last_good_is_not_blocked_release(self):
        self.assertEqual(self.gate.last.rel.rid, "R-0623")

    def test_override_is_recorded(self):
        r = self.res[3]
        with self.assertRaises(PermissionError):
            self.gate.override(r, "Daniel Price", "x", "y")
        with self.assertRaises(ValueError):
            self.gate.override(r, "Sarah Whitfield", " ", "y")
        g = GT.Gate(tasks=TASKS[:10], cal=self.gate.cal)
        rec = g.override(replace(r), "Sarah Whitfield", "test", "five")
        self.assertEqual(rec["by"], "Sarah Whitfield")
        self.assertIn("OVERRIDE", g.log[-1])

    def test_uncalibrated_judge_blocks(self):
        g = GT.Gate(tasks=TASKS[:20], judge=J.OfflineJudge(pin="new"),
                    cal=self.gate.cal)
        r = g.evaluate(GT.JUNE[0])
        self.assertFalse(r.passed)
        self.assertIn("judge not calibrated", r.reasons[0])

    def test_cost_drift_blocks(self):
        g = GT.Gate(tasks=TASKS[:40], cal=self.gate.cal)
        g.record(g.evaluate(GT.REHEARSAL))
        r = g.evaluate(GT.JUNE[8])
        self.assertTrue(any(x.startswith("cost per task")
                            for x in r.reasons))

    def test_rehearsal_and_registry_line(self):
        r = self.gate.evaluate(GT.REHEARSAL)
        self.assertTrue(r.passed)
        self.assertEqual(r.exact_pct, 100.0)
        line = GT.registry_line(r, self.gate)
        h = M.resolve(M.load("servicing-1.1.0"))
        self.assertIn(M.manifest_hash(h)[:12], line)


class OnlineHarvestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prods = O.production()

    def test_board(self):
        b = O.board(self.prods)
        self.assertEqual(b.traces, 6001)
        self.assertEqual(b.forbidden, 0)
        self.assertEqual(len(b.weekly), 4)
        self.assertTrue(all(n == 150 for _, n, _ in b.weekly))

    def test_candidates_carry_source_run(self):
        cands = H.label(H.clusters(self.prods))
        self.assertEqual(len(cands), 7)
        for c in cands:
            self.assertTrue(c.task.source.startswith("run P-"))
            self.assertEqual(c.labeled_by, "Keisha Navarro")
        self.assertIn("P-0624-HOTEL", cands[-1].run)

    def test_frozen_between_cuts(self):
        cands = H.label(H.clusters(self.prods))
        with self.assertRaises(H.FrozenBetweenCuts):
            H.admit(TASKS, cands, "2026-06-29")
        new = H.admit(TASKS, cands, "2026-07-06")
        self.assertEqual(len(new), 647)
        self.assertEqual({t.version for t in new}, {"gs-2026.07"})

    def test_march_set_misses_april(self):
        rel = A.Release("R-0414", "2026-04-14", "batch", "tool server",
                        reads_ledger=False)
        mix = [m for m in O.MIX if m[0] not in ("split_payment",
                                                 "two_timeouts")]
        ps = O.production(n=600, seed=414, month=4, mix=mix, release=rel)
        march = G.build(G.MARCH)
        self.assertEqual(H.missing_classes(march, H.clusters(ps)),
                         ["already_refunded"])


if __name__ == "__main__":
    unittest.main()
