"""Chapter 44: the storm day replays to the incident record."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from common.text import too_long

from . import demo, pilot, ramp, record, review
from .day import STORM_CHANGES, generate, in_window, stamp
from .desk import Desk
from .replay import latency_at, latency_while_newest, run, t, variant


class Day(unittest.TestCase):
    def test_storm_window_holds_41000_changes(self):
        self.assertEqual(in_window(generate()), STORM_CHANGES)

    def test_records_are_deterministic(self):
        a, b = generate(), generate()
        self.assertEqual([c.cid for c in a[:50]], [c.cid for c in b[:50]])

    def test_log_stamps_carry_cdt(self):
        self.assertEqual(stamp(t(14, 40)), "2026-09-10T14:40:00-05:00")


class AsRun(unittest.TestCase):
    r = run("as-run")

    def test_budget_spent_at_noon(self):
        self.assertEqual(round(self.r.budget_spent_at), t(12, 5))
        self.assertLess(self.r.paged_at, self.r.budget_spent_at)

    def test_peak_about_9000_at_2_40(self):
        self.assertEqual(self.r.peak_at, t(14, 40))
        self.assertAlmostEqual(self.r.peak_depth, 9_000, delta=150)

    def test_latency_reads_20_minutes(self):
        self.assertAlmostEqual(latency_at(self.r, t(14)), 20, delta=1)
        self.assertLess(latency_while_newest(self.r), 22)

    def test_dashboard_hides_the_oldest_card(self):
        self.assertGreater(self.r.oldest_at_peak, 180)

    def test_cleared_in_eleven_hours(self):
        self.assertEqual(self.r.cleared_at, t(22, 40))
        self.assertAlmostEqual(self.r.hours_to_clear, 11.0)

    def test_verified_98_7(self):
        self.assertAlmostEqual(self.r.verified_rate, 0.987, delta=0.0006)

    def test_surge_rule_stays_inside_500(self):
        self.assertLessEqual(self.r.surge_max_usd, 500)

    def test_held_work_done_by_friday_morning(self):
        self.assertIsNotNone(self.r.held_done_at)
        self.assertLess(self.r.held_done_at, 24 * 60 + t(9))


class Failure(unittest.TestCase):
    def test_no_priority_misses_more_departures(self):
        self.assertGreater(run("no-priority").missed,
                           3 * run("as-run").missed)

    def test_fare_order_is_worse_than_departure(self):
        self.assertGreater(run("fare").missed, run("as-run").missed)

    def test_redesign_keeps_departures(self):
        r = run("redesigned")
        self.assertLess(r.missed, 20)
        self.assertLess(r.peak_depth, 3_000)

    def test_rota_clears_before_dark(self):
        self.assertLess(run("redesigned-rota").cleared_at, t(18))

    def test_no_emergency_moves_work_to_people(self):
        self.assertGreater(run("no-emergency").to_people, 30_000)
        # and the reserve alone, without the other levers, puts that
        # work on the desk: a higher peak than the day as it ran
        alone = run(variant("reserve", emergency_at=t(11, 40)))
        self.assertGreater(alone.peak_depth, run("as-run").peak_depth)

    def test_widen_doubles_unreviewed_dollars(self):
        a, w = run("as-run"), run("widen-1000")
        self.assertGreater(w.surge_usd, 1.4 * a.surge_usd)
        self.assertGreater(w.surge_max_usd, 900)


class DeskOrder(unittest.TestCase):
    def test_newest_first_takes_the_last_card(self):
        cs = [c for c in generate() if c.card][:20]
        d = Desk(order="newest")
        for c in cs:
            d.add(c)
        for m in range(6):
            d.work(t(12) + m, 1)
        self.assertEqual(d.decided[0].cid, cs[-1].cid)


class Ramp(unittest.TestCase):
    def test_monthly_agent_share(self):
        want = {"Dec 2025": 0.9, "Mar 2026": 4.0, "Apr 2026": 2.5,
                "May 2026": 6.0, "Jun 2026": 14.0, "Jul 2026": 14.0,
                "Aug 2026": 36.0, "Sep 2026": 44.0}
        for m, v in want.items():
            self.assertAlmostEqual(ramp.agent_share(m) * 100, v,
                                   delta=0.05)

    def test_by_type_gate_holds_u1(self):
        g = {x.kind: x.opens for x in ramp.gates({"R1", "V1"})}
        self.assertFalse(g["U1"])
        self.assertTrue(g["R1"])

    def test_traffic_blend_hides_a_bad_type(self):
        self.assertGreaterEqual(
            ramp.traffic_verified({"R1", "V1", "C1"}), 0.990)


class Review(unittest.TestCase):
    def test_recovered_in_three_days(self):
        self.assertEqual(review.recovered_on(review.daily_verified()), 13)

    def test_three_designs(self):
        self.assertEqual([d.record for d in review.DESIGNS],
                         ["R-RBK-1", "R-RFD-1", "R-PLT-1"])

    def test_record_is_ordered(self):
        ats = [e.at for e in record.timeline()]
        self.assertEqual(ats, sorted(ats))
        self.assertEqual(len(record.spans()), len(ats) + 1)

    def test_pilot_card(self):
        self.assertEqual(pilot.CARD["Sep 2026"][0], 0.44)


class Output(unittest.TestCase):
    def test_every_part_fits_70_columns(self):
        for part in ("pilot", "ramp", "day", "compare", "record",
                     "capacity", "recovery", "card"):
            buf = io.StringIO()
            with redirect_stdout(buf):
                demo.main(["--part", part])
            self.assertEqual(too_long(buf.getvalue()), [], part)


if __name__ == "__main__":
    unittest.main()
