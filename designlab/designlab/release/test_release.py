"""Offline tests for the Chapter 39 release lab. No model call, no key.

    DESIGNLAB_OFFLINE=1 python3 -m unittest release.test_release -v
"""
from __future__ import annotations

import contextlib
import io
import unittest
from types import SimpleNamespace

from common.text import too_long

from . import abtest as AB
from . import bundle as B
from . import canary as C
from . import demo as D
from . import gate as RG
from . import log as L
from . import pipeline as P
from . import rollback as R
from . import shadow as S


class TestBundle(unittest.TestCase):
    def test_six_kinds_hashed_together(self):
        b = B.base()
        self.assertEqual(set(b.parts()), set(B.KINDS))
        self.assertEqual(len(b.hash), 12)
        self.assertEqual(b.hash, B.base().hash)

    def test_console_edit_is_a_new_bundle(self):
        b, e = B.base(), D.console_edit()
        self.assertNotEqual(b.hash, e.hash)
        self.assertEqual(b.changed(e), ["prompt"])
        self.assertEqual(len(b.detail(e)), 1)

    def test_r0723_changes_only_the_harness(self):
        self.assertEqual(D.july23().changed(D.r0723()), ["harness"])


class TestLog(unittest.TestCase):
    def test_counts(self):
        c = L.counts()
        self.assertEqual(c["releases"], 23)
        self.assertEqual(c["kinds"], 6)
        self.assertEqual(c["june_rule"], 9)
        self.assertEqual(c["rolled_back"], ["R-0723", "R-0819"])
        self.assertEqual(c["production_regressions"], 0)

    def test_card_fits(self):
        self.assertEqual(too_long("\n".join(L.card())), [])


class TestGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = RG.BundleGate(tasks=D._gate_tasks())

    def test_split_payment_blocks_without_the_tool_fix(self):
        res = self.g.evaluate(RG.Candidate("R-0710", "2026-07-10",
                                           "policy", "policy"))
        self.assertFalse(res.passed)
        self.assertEqual({v[0][1] for v in res.failing.values()},
                         {"split_payment"})

    def test_split_fix_passes(self):
        res = self.g.evaluate(RG.Candidate("R-0713", "2026-07-13",
                                           "split", "tool", splits=True))
        self.assertTrue(res.passed)

    def test_split_to_an_unpaid_card_is_forbidden(self):
        t = next(t for t in self.g.tasks if t.cls == "split_payment")
        tr = RG.run(t, RG.Candidate("x", "d", "c", splits=True), 0)
        tr.effects[0] = ("refund", tr.effects[0][1], "9999")
        self.assertIn("refund_other_card", RG.split_forbidden(t, tr))


class TestWhatIf(unittest.TestCase):
    def test_step_budget_16_changes_nothing_12_holds(self):
        b = B.base()
        h, ov = D.harness_101(16)
        w = RG.whatif(b, b.with_part("harness", "servicing-1.0.1", h), ov)
        self.assertEqual(len(w.divergent), 0)
        h, ov = D.harness_101(12)
        w = RG.whatif(b, b.with_part("harness", "servicing-1.0.1", h), ov)
        self.assertTrue(w.holds)

    def test_prompt_change_marks_chat_spans(self):
        b = B.base()
        c = b.with_prompt("refund-reason@1.4", "new text")
        w = RG.whatif(b, c)
        self.assertGreater(w.marked_runs, 0)


class TestCanary(unittest.TestCase):
    def test_verified_canary_rolls_back_latency_does_not(self):
        v = C.run("refund", 0.037, 0.007, seed=43)
        self.assertEqual(v.verdict, "rolled_back")
        self.assertEqual(v.stopped_at.share, 0.25)
        lat = C.run("refund", 0.037, 0.007, seed=43, measure="latency")
        self.assertEqual(lat.verdict, "full")

    def test_small_canary_misses_rare_defects(self):
        self.assertAlmostEqual(C.p_detect(1e-4, 5000), 0.393, places=3)


class TestRollback(unittest.TestCase):
    def test_every_inflight_state_has_a_rule(self):
        b, c = D.july23(), D.r0723()
        runs = R.inflight()
        for r in runs:
            r.bundle = c.hash
        plan = R.rollback(c, b, runs, "t")["plan"]
        self.assertEqual([len(plan[s]) for s in R.STATES],
                         [4, 7, 6, 23, 59])

    def test_downcast_only_when_lossless(self):
        ok = R.MemRecord("a", 3, {"seat": "aisle", "assist_need": None})
        bad = R.MemRecord("b", 3, {"seat": "aisle", "assist_need": "wchr"})
        self.assertEqual(R.downcast(ok).schema, 2)
        self.assertIsNone(R.downcast(bad))


class TestExposure(unittest.TestCase):
    def test_shadow_sends_no_effect(self):
        sh = S.run()
        self.assertEqual(len(sh.tool.calls), sh.runs)
        self.assertTrue(0.02 < sh.n_differ / sh.runs < 0.05)
        self.assertEqual(sh.reviewed, sh.n_differ)

    def test_sample_size_and_peeking(self):
        self.assertEqual(AB.sample_size(0.09, 0.07), 2888)
        end, peek = AB.peeking(trials=400)
        self.assertGreater(peek, 2 * end)

    def test_bandit_moves_traffic_before_the_verdict(self):
        share, bad = AB.bandit(days=5)
        self.assertGreater(share[2], 0.9)
        self.assertGreater(bad[1], bad[0])


class TestDeploy(unittest.TestCase):
    def test_refusals(self):
        p = P.Pipeline()
        b, c = D.july23(), D.r0723()
        rec = B.Record("R-0723", "d", c, b.hash, ["harness"], "o")
        p.submit(rec)
        with self.assertRaises(P.Refused):
            p.deploy(c, "refund", "canary", 0.05, "t")
        p.gate_passed(rec, "t")
        p.deploy(c, "refund", "canary", 0.05, "t")
        with self.assertRaises(P.Refused):
            p.deploy(D.console_edit(), "refund", "full", 1.0, "t")
        with self.assertRaises(P.Refused):
            p.allow("bandit", "refund")
        with self.assertRaises(P.Refused):
            p.allow("ab", "credit")
        p.allow("ab", "notify")
        p.allow("bandit", "option_order")
        p.rollback(c, "refund", "t")
        self.assertEqual(p.active["refund"], b.hash)


class TestDemo(unittest.TestCase):
    def test_every_line_fits(self):
        buf = io.StringIO()
        a = SimpleNamespace(alone=True, steps=16, task="refund")
        with contextlib.redirect_stdout(buf):
            for name, fn in D.PARTS.items():
                if name not in ("whatif",):
                    fn(a)
        self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
