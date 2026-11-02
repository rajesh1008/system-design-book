"""Chapter 28 tests. Offline, seeded; small fleets for speed."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import replace

from common.text import too_long

from . import scenarios as S
from .fare_watch import V100, V101, V110, Actor, Control, Verifier
from .lint import lint, passed
from .spec import (FARE_WATCH, WAIVER_WATCH, fare_watch_v0, model_stop,
                   no_state, self_verify)
from .state import Persisted
from .trigger import Triggers
from .world import ACTOR, at, fare_world

N = 200


class LintTest(unittest.TestCase):
    def test_live_loops_pass_all_seven(self):
        self.assertEqual(passed(FARE_WATCH), 7)
        self.assertEqual(passed(WAIVER_WATCH), 7)

    def test_first_build_and_injections_fail(self):
        self.assertEqual(passed(fare_watch_v0()), 1)
        for inj, prop in ((model_stop, "stop"), (no_state, "state"),
                          (self_verify, "verify")):
            bad = [f.prop for f in lint(inj(FARE_WATCH)) if not f.ok]
            self.assertEqual(bad, [prop])


class OpeningTest(unittest.TestCase):
    def test_green_report_with_no_reads(self):
        fw = fare_world(N)
        a, v = Actor(fw, V100), Verifier(fw)
        h = a.run_hour(S.JUNE14)
        r = v.check_hour(S.JUNE14, h, a.store)
        self.assertEqual(h.claimed, N)
        self.assertEqual(r["trail_reads"], 0)
        self.assertFalse(r["green"])
        self.assertIn(f"{N:,} watches", h.report)

    def test_fixed_build_verifies_green(self):
        fw = fare_world(N)
        a, v = Actor(fw, V110), Verifier(fw)
        for hr in range(S.JUNE14, S.JUNE14 + 7):
            h = a.run_hour(hr)
            self.assertTrue(v.check_hour(hr, h, a.store)["green"])


class StopTest(unittest.TestCase):
    def test_night_repeats_then_dedupes(self):
        self.assertEqual(S.night(V101, False)["model_calls"], 41)
        r = S.night(V110, True)
        self.assertEqual((r["runs"], r["model_calls"]), (6, 1))

    def test_detector_stops_within_five(self):
        r = S.night(replace(V101, version="d", detector=True), False)
        self.assertEqual(r["status"], "paused")
        self.assertLessEqual(r["model_calls"], 5)

    def test_injected_stalls_all_stop(self):
        inj = S.injections(per_kind=5, n=N)
        for steps in inj.values():
            self.assertTrue(all(0 < s <= 5 for s in steps))


class TriggerTest(unittest.TestCase):
    def test_timer_fires_once_across_sweepers(self):
        rs = Persisted().rs
        a, b = Triggers(rs, "x"), Triggers(rs, "x")
        a.schedule("sweep@00", at(0))
        self.assertEqual(len(a.due(at(0, 1))) + len(b.due(at(0, 1))), 1)

    def test_run_key_dedupes(self):
        t = Triggers(Persisted().rs, "x")
        self.assertTrue(t.wake(("W-1", 3, "ab"), at(3)))
        self.assertFalse(t.wake(("W-1", 3, "ab"), at(3, 5)))


class BudgetTest(unittest.TestCase):
    def test_tight_loop_day_refuses_and_never_overspends(self):
        r = S.replay(days=1, first_day=4, n=N, loop_day=0.25)
        self.assertEqual(r["runs_over"], [])
        self.assertEqual(r["enf"].over(), [])
        self.assertTrue(any(e.get("stop") == "loop-day"
                            for e in r["enf"].log))


class StateTest(unittest.TestCase):
    def wrong(self, kind):
        r = S.replay(days=1, n=N, store_kind=kind, restart_every=6)
        return sum(int(w.split()[1]) for _h, _x, v in r["hours"]
                   for w in v["why"] if w.startswith("vouchers "))

    def test_memory_state_double_pays_and_verifier_sees_it(self):
        self.assertGreater(self.wrong("memory"), 0)
        self.assertEqual(self.wrong("run_store"), 0)


class ChangeTest(unittest.TestCase):
    def test_scope_and_permission(self):
        fw = fare_world(3)
        w, g = fw.list[0], fw.w.gateway
        r = g.call(ACTOR, "payments", "refund_ticket",
                   {"itinerary_id": w.booking})
        self.assertEqual(r.reason, "not_in_scope")
        args = {"itinerary_id": w.booking, "amount_usd": "40.00",
                "reason": "service"}
        pid = Control(fw).permit("voucher_issue", args)
        self.assertTrue(g.call(ACTOR, "payments", "voucher_issue", args,
                               permission=pid).ok)
        self.assertFalse(g.call(ACTOR, "payments", "voucher_issue",
                                args, permission=pid).ok)
        self.assertEqual(Control(fw).voucher("2026-06-14", 128.35),
                         "over-cap")


class DemoWidthTest(unittest.TestCase):
    def test_lint_part_fits(self):
        from .demo import part_lint
        buf = io.StringIO()
        with redirect_stdout(buf):
            part_lint()
        self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
