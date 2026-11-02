"""Offline tests for Chapter 37: objectives, burn alerts, budgets, the
two July incidents, stops, the game day, runbooks, and reviews."""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from common.client import FixtureTransport

from . import (budget, burn, card, daily, gameday, july8, live, review,
               runbook, stop, storm)
from .objectives import BY_KEY, FIVE, UPTIME, Reading, read
from .records import Records, at, hm


class July8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rec = july8.build()
        cls.s = july8.summary(cls.rec)

    def test_up_and_wrong(self):
        self.assertEqual(self.s["tasks"], 1180)
        self.assertEqual(self.s["dropped"], 40)
        self.assertAlmostEqual(self.s["verified"] / 1180, 0.960, 3)
        self.assertGreater(self.s["uptime"], 0.9997)

    def test_uptime_never_alerts(self):
        self.assertEqual(burn.scan(UPTIME, self.rec.tasks, july8.MOVED,
                                   july8.STOPPED), [])

    def test_slice_pages_before_desk(self):
        al = burn.scan(BY_KEY["verified"], self.rec.tasks, july8.MOVED,
                       july8.STOPPED, kind="rebooking")
        page = [a for a in al if a.rule == "page"][0]
        self.assertEqual(hm(page.at), "08:42")
        self.assertLess(page.at, july8.DESK_SAW)

    def test_aggregate_only_tickets(self):
        al = burn.scan(BY_KEY["verified"], self.rec.tasks, july8.MOVED,
                       july8.STOPPED)
        self.assertEqual([a.rule for a in al], ["ticket"])

    def test_code_check(self):
        t, why = july8.first_code_flag(self.rec)
        self.assertEqual(hm(t.ended), "07:53")
        self.assertIn("number", why)

    def test_pinned_is_clean(self):
        rec = july8.build(pinned=True)
        self.assertEqual(july8.summary(rec)["dropped"], 0)
        self.assertIsNone(july8.first_code_flag(rec)[0])


class Objectives(unittest.TestCase):
    def test_five_owned_and_sourced(self):
        self.assertEqual(len(FIVE), 5)
        for o in FIVE:
            self.assertTrue(o.owner and o.source)
            self.assertNotEqual(o.source, "actor")

    def test_missing_source_is_unknown(self):
        rec = july8.build()
        rec.missing = {"reconciler"}
        r = read(BY_KEY["verified"], rec, july8.MOVED, july8.STOPPED)
        self.assertEqual(r.status, "unknown")

    def test_empty_is_unknown(self):
        r = read(BY_KEY["backlog"], Records(), july8.MOVED,
                 july8.STOPPED)
        self.assertEqual(r.status, "unknown")


class Budget(unittest.TestCase):
    def test_freeze_rule(self):
        mk = lambda bad: Reading("verified", 1000 - bad, 1000, 10.0,
                                 bad, "")
        self.assertEqual(budget.decide(mk(4)).state, "ship")
        self.assertEqual(budget.decide(mk(6)).state, "sign-off")
        d = budget.decide(mk(11))
        self.assertEqual((d.state, d.rung), ("freeze", "propose-only"))

    def test_unauthorized_has_no_budget(self):
        r = Reading("unauthorized", 999, 1000, 0.0, 1, "")
        self.assertEqual(budget.decide(r).state, "stop")

    def test_unknown_is_not_met(self):
        r = Reading("cost", 0, 0, 0.0, 0, "unknown")
        self.assertEqual(budget.decide(r).state, "sign-off")

    def test_rebooking_window(self):
        rows = daily.series()
        self.assertLess(daily.on(rows, date(2026, 7, 7))[4], 0.5)
        self.assertGreater(daily.on(rows, date(2026, 7, 8))[4], 0.8)
        self.assertLess(daily.on(rows, date(2026, 8, 31))[4], 0.3)
        pinned = daily.series(pinned=True)
        self.assertLess(daily.on(pinned, date(2026, 7, 8))[4], 0.5)

    def test_restore(self):
        self.assertFalse(budget.can_restore(1.2, 0, "a", "a")[0])
        self.assertFalse(budget.can_restore(0.4, 1, "a", "a")[0])
        self.assertFalse(budget.can_restore(0.4, 0, "b", "a")[0])
        self.assertTrue(budget.can_restore(0.4, 0, "a", "a")[0])


class Storm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st = storm.simulate()

    def test_billed_not_counted(self):
        self.assertGreater(self.st.billed(), 500_000)
        self.assertEqual(self.st.counted(), 0)

    def test_latency_pages_sunday_evening(self):
        al = burn.scan(BY_KEY["latency"], self.st.records.tasks,
                       storm.START, storm.END)
        page = [a for a in al if a.rule == "page"][0]
        self.assertEqual(page.at.date(), date(2026, 7, 26))
        self.assertEqual(hm(page.at), "19:28")
        self.assertEqual(hm(self.st.first_limited()), "18:00")
        self.assertGreater(storm.hidden_hours(self.st, page.at), 40)

    def test_provider_count_pages_early(self):
        t = gameday.usage_page(self.st)
        self.assertLess(t - storm.START, timedelta(hours=1))

    def test_one_retry_layer(self):
        st = storm.simulate(harness=1, requeue=False)
        self.assertLess(st.billed(), self.st.billed() / 100)


class Stops(unittest.TestCase):
    def test_times(self):
        self.assertEqual(round(stop.july8().seconds), 64)
        self.assertEqual(round(stop.storm().seconds), 116)
        self.assertEqual(round(stop.median(
            [stop.july8().seconds, stop.storm().seconds])), 90)

    def test_tier_two_does_not_stop_a_loop(self):
        s = stop.storm([(9, 2, "x", "")])
        self.assertIsNone(s.seconds)
        self.assertEqual(s.blocked["tier 2"], "not blocked")

    def test_tier_three_first(self):
        self.assertEqual(round(stop.storm([(9, 3, "x", "")]).seconds),
                         72)


class GameDay(unittest.TestCase):
    def test_legacy_falsifies_one(self):
        res = gameday.run(legacy=True)
        self.assertEqual(len(res), 6)
        self.assertEqual([r.key for r in res if not r.held], ["G6"])

    def test_fixed_holds_all(self):
        self.assertTrue(all(r.held for r in gameday.run(legacy=False)))

    def test_uptime_only_injection_is_green(self):
        self.assertFalse(gameday.g_uptime_only().held)


class Runbooks(unittest.TestCase):
    def test_runbooks_clean(self):
        for rb in runbook.RUNBOOKS:
            self.assertEqual(runbook.lint(rb, "model gateway"), [])

    def test_old_runbook_fails(self):
        self.assertEqual(len(runbook.lint(runbook.OLD)), 5)

    def test_storm_runbook_tier_three(self):
        self.assertEqual(runbook.STORM.stop_tier, 3)

    def test_render_fits(self):
        for rb in runbook.RUNBOOKS:
            for ln in runbook.render(rb):
                self.assertLessEqual(len(ln), 70)


class Reviews(unittest.TestCase):
    def test_closed(self):
        for r in review.REVIEWS:
            self.assertEqual(review.gate(r), [])

    def test_gate_catches(self):
        r = review.Review("x", "y", effects={"held": 2},
                          temporary={"tier one": "pulled"},
                          factors=["Ben failed to check"],
                          actions=[review.Action("fix", "", "")])
        self.assertEqual(len(review.gate(r)), 7)


class Card(unittest.TestCase):
    def test_card(self):
        rows = dict((k, v) for k, v, _ in card.card())
        self.assertIn("median 90 s", rows["time to stop"])
        self.assertTrue(rows["objectives"].startswith("5"))


class LiveReplay(unittest.TestCase):
    def test_replay(self):
        out = live.run(FixtureTransport(live.FIXTURES), record=False)
        self.assertIn("72 calls", out[-1])
        self.assertTrue(any("pass^3 12/12" in ln for ln in out))
        self.assertTrue(all(len(ln) <= 70 for ln in out))


if __name__ == "__main__":
    unittest.main()
