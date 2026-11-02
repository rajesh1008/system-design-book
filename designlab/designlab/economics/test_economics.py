"""Chapter 38 tests: the bill, the close, the gateway, the replay,
chargeback, and the card. Offline; no model call."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from dataclasses import replace
from datetime import timedelta

from common.text import too_long
from reliability.records import at

from . import bill, bound, card, chargeback, demo, outcome, replay
from .policy import DR38, JULY, JULY_COUNTING, Gateway, Refused


class Bill(unittest.TestCase):
    def test_storm_is_billed_calls_times_price(self):
        self.assertEqual(bill.weekend().billed(), 704_949)
        self.assertAlmostEqual(bill.storm_usd(), 11_406.07, places=2)

    def test_july_is_about_three_times_june(self):
        r = bill.total("July") / bill.total("June")
        self.assertGreater(r, 2.9)
        self.assertLess(r, 3.1)

    def test_input_only_estimate_misses_the_output(self):
        self.assertLess(bill.estimate_usd(), bill.storm_usd() / 80)

    def test_per_token_price_falls_in_july(self):
        self.assertLess(bill.per_mtok("July"), bill.per_mtok("June"))


class Close(unittest.TestCase):
    def test_july_closes_at_2_02_above_the_band(self):
        c = outcome.close("July")
        self.assertEqual(round(c.total, 2), 2.02)
        self.assertGreater(c.total, outcome.BAND["July"][2])

    def test_drivers_alone_sit_inside_the_band(self):
        c = outcome.close("July")
        self.assertLessEqual(c.drivers, outcome.BAND["July"][2])

    def test_identity_rule_still_misses_on_inc5(self):
        c = outcome.close("July", "identity")
        self.assertEqual(round(c.total, 2), 1.80)
        self.assertEqual(c.pooled, 0.0)
        self.assertGreater(c.total, outcome.BAND["July"][2])

    def test_august_is_1_61_inside_its_band(self):
        c = outcome.close("August")
        lo, _m, hi = outcome.BAND["August"]
        self.assertEqual(round(c.total, 2), 1.61)
        self.assertTrue(lo <= c.total <= hi)

    def test_kinds_average_to_the_whole(self):
        from corpus.traces import KINDS
        k = outcome.kinds("July")
        avg = sum(k[n] * s for n, s in KINDS)
        self.assertAlmostEqual(avg, outcome.close("July").total,
                               places=2)

    def test_storm_week_tokens_down_outcomes_up(self):
        rows = {n: (t, p) for n, t, p in outcome.weekly()}
        before, storm = rows["Jul 13-19"], rows["Jul 20-26"]
        self.assertLess(storm[0], before[0])
        self.assertGreater(storm[1], before[1])


class Bound(unittest.TestCase):
    def test_july_unbounded_and_over_the_run_budget(self):
        self.assertIsNone(bound.per_trigger(bound.JULY))
        self.assertGreater(bound.per_run(bound.JULY), 0.25)

    def test_august_fits_the_run_budget(self):
        self.assertLessEqual(bound.per_trigger(bound.AUGUST), 0.25)


T = at("2026-07-25", "02:14")


def _small_day(usd: float = 1.0):
    return replace(DR38, loops=(
        replace(DR38.loops[0], loop_day_usd=usd), DR38.loops[1]))


class GatewayRules(unittest.TestCase):
    def test_release_counts_nothing_worst_counts_worst(self):
        for p, want in ((JULY, 0.0), (DR38, 0.2)):
            g = Gateway(p)
            billed = g.call("waiver-watch", "r1", T, 0.2, None)
            self.assertEqual(billed, 0.2)
            self.assertEqual(g.counted, want)

    def test_refusal_moves_no_counter(self):
        g = Gateway(_small_day())
        for i in range(5):
            g.call("waiver-watch", f"r{i}", T, 0.2, None)
        with self.assertRaises(Refused):
            g.call("waiver-watch", "r9", T, 0.2, None)
        self.assertAlmostEqual(g.spent("loop:waiver-watch:2026-07-25"),
                               1.0)
        self.assertAlmostEqual(g.spent("day:2026-07-25"), 1.0)

    def test_stop_holds_all_day_and_resets_at_midnight(self):
        g = Gateway(_small_day())
        for i in range(4):
            g.call("waiver-watch", f"r{i}", T, 0.2, None)
        with self.assertRaises(Refused):
            g.call("waiver-watch", "r5", T, 0.25, None)
        with self.assertRaises(Refused):     # small call, still stopped
            g.call("waiver-watch", "r6", T, 0.01, None)
        sun = at("2026-07-26", "00:00")
        self.assertEqual(g.call("waiver-watch", "r7", sun, 0.2, None),
                         0.2)

    def test_page_at_half_once(self):
        g = Gateway(_small_day(2.0))
        for i in range(9):
            g.call("waiver-watch", f"r{i}", T, 0.2, None)
        pages = [e for e in g.events if e[2].startswith("loop:")]
        self.assertEqual([e[1] for e in pages], ["page 50%"])


class Replay(unittest.TestCase):
    def test_as_run_matches_the_invoice_line(self):
        r = replay.run(JULY)
        self.assertAlmostEqual(r.billed, bill.storm_usd(), places=2)
        self.assertEqual(r.counted, 0.0)
        self.assertGreater(r.servicing_429_min, 0)

    def test_dr38_caps_the_weekend_at_400(self):
        r = replay.run(DR38)
        self.assertLessEqual(r.billed, 400.0)
        self.assertGreater(r.billed, 399.0)
        self.assertEqual(r.servicing_429_min, 0)
        kinds = [w for _t, w, k in r.events if k.startswith("loop:")]
        self.assertEqual(kinds, ["page 50%", "stop"] * 2)

    def test_page_comes_before_stop_each_day(self):
        ev = [(t, w) for t, w, k in replay.run(DR38).events
              if k.startswith("loop:")]
        self.assertLess(ev[0][0], ev[1][0])
        self.assertLess(ev[1][0] - ev[0][0], timedelta(hours=2))

    def test_july_budgets_counting_would_have_held(self):
        self.assertLessEqual(replay.run(JULY_COUNTING).billed, 20.0)

    def test_small_envelope_stops_the_fare_watch(self):
        r = replay.run(replace(DR38, envelope_usd=200.0))
        self.assertGreater(r.fare_refused, 0)
        self.assertEqual(replay.run(DR38).fare_refused, 0)

    def test_rate_share_protects_capacity_not_money(self):
        usd, over = replay.rate_share_only()
        self.assertEqual(over, 0)
        self.assertGreater(usd, 10 * replay.run(DR38).billed)


class Chargeback(unittest.TestCase):
    def test_statement_adds_to_invoice_plus_platform(self):
        for rule in ("pool", "identity"):
            st = chargeback.statement("July", rule)
            self.assertAlmostEqual(
                sum(r["total"] for r in st.values()),
                bill.total("July") + chargeback.PLATFORM_FIXED, places=6)

    def test_storm_goes_to_the_loop_owner(self):
        st = chargeback.statement("July")
        self.assertAlmostEqual(st["platform engineering"]["incident"],
                               bill.storm_usd(), places=6)
        self.assertEqual(st["customer operations"]["incident"], 0.0)

    def test_unallocated_gets_no_platform_share(self):
        st = chargeback.statement("July")
        self.assertEqual(st["unallocated"]["platform"], 0.0)
        self.assertGreater(st["unallocated"]["model"], 0.0)

    def test_use_cases_add_to_the_cent(self):
        u = chargeback.by_use_case("August")
        servicing = bill.invoice("August")[0].usd
        self.assertAlmostEqual(sum(u.values()), servicing, places=6)


class Card(unittest.TestCase):
    def test_cells(self):
        values = [c[1] for c in card.cells()]
        self.assertEqual(values, ["$1.61", "100%", "$400"])

    def test_august_never_pages(self):
        b = DR38.budget("waiver-watch")
        self.assertLess(max(card.AUGUST_WAIVER_DAYS),
                        DR38.alert * b.loop_day_usd)
        self.assertAlmostEqual(sum(card.AUGUST_WAIVER_DAYS),
                               bill.WAIVER_WATCH["August"], places=6)


class Output(unittest.TestCase):
    def test_every_line_fits_70(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            demo.main([])
            demo.main(["--part", "policy", "--envelope", "200"])
            demo.main(["--part", "chargeback", "--by", "use-case"])
        self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
