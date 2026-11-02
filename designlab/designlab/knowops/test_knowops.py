"""Tests for designlab.knowops (Chapter 24)."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime

from common.clock import FixedClock
from common.text import too_long
from common.trail import TrailWriter
from corpus.fall2 import CDT, generate_fall2
from memory import (Draft, MemoryStore, SessionToken, Source, by_record)
from memory.store import RETENTION_DAYS

from knowops import demo
from knowops.expiry import RETENTION_V2, classify, review_legacy, ttl_for
from knowops.freshness import CONTRACTS, check
from knowops.pilot import fixed_choice, packet, replay_choice, where
from knowops.verify import destination_verifier, pnr_reconciler
from knowops.weekly import fresh_sample, golden, run

T = generate_fall2(2026)
IT = T["fall2_itins"][0]
CONF = Source("CON-1", "customer-confirmed", "yes")


def store(ttl=None):
    clock = FixedClock("2026-05-19T11:00:00-05:00")
    return MemoryStore(clock, TrailWriter(clock=clock), ttl_days=ttl)


def tok():
    return SessionToken("SES-1", IT["customer_id"], IT["itinerary_id"])


class TestFreshness(unittest.TestCase):
    def test_every_contract_has_owner_and_action(self):
        for c in CONTRACTS:
            self.assertTrue(c.owner and c.on_stale and c.record)

    def test_booking_limit_and_unknown(self):
        self.assertEqual(check("booking record", 14 * 60), "fresh")
        self.assertEqual(check("booking record", 16 * 60), "stale")
        self.assertEqual(check("booking record", None), "unknown")

    def test_notices_tighten_during_event(self):
        self.assertEqual(check("waivers and notices", 3600), "fresh")
        self.assertEqual(check("waivers and notices", 3600, True), "stale")


class TestMemoryExtension(unittest.TestCase):
    def test_default_unchanged(self):
        r = store().write(tok(), Draft("seat", "aisle", "standing",
                                       CONF, 0.9))
        days = (datetime.fromisoformat(r.expires_at)
                - datetime.fromisoformat(r.recorded_at)).days
        self.assertEqual(days, RETENTION_DAYS)

    def test_ttl_by_subject(self):
        s = store(RETENTION_V2)
        d = s.write(tok(), Draft("destination", "Denver", "standing",
                                 CONF, 0.9))
        a = s.write(tok(), Draft("seat", "aisle", "standing", CONF, 0.9))
        span = lambda r: (datetime.fromisoformat(r.expires_at)
                          - datetime.fromisoformat(r.recorded_at)).days
        self.assertEqual(span(d), 30)
        self.assertEqual(span(a), 365)

    def test_supersede_by_record(self):
        s = store(RETENTION_V2)
        s.write(tok(), Draft("destination", "Denver", "standing", CONF, .9))
        s.write(tok(), Draft("seat", "aisle", "standing", CONF, .9))
        kept, dropped = by_record(s.read(tok()), {
            "record_id": IT["itinerary_id"], "destination": "PHX"},
            s.trail)
        self.assertEqual([r.subject for r in kept], ["seat"])
        self.assertEqual(dropped[0][2], "PHX")
        self.assertIn("superseded_by_record", s.trail.lines[-1])


class TestExpiry(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("prefers Denver"), "destination")
        self.assertEqual(classify("prefers aisle seat"), "seat")
        self.assertIsNone(classify("VIP"))

    def test_ttls(self):
        self.assertEqual(ttl_for("destination"), 30)
        self.assertEqual(ttl_for("seat"), 365)
        self.assertEqual(ttl_for(None), 180)

    def test_legacy_note(self):
        n = T["fall2_note"][0]
        now = datetime(2026, 5, 19, 11, 31, tzinfo=CDT)
        self.assertEqual(review_legacy(n, now)[0], "expire")
        self.assertEqual(review_legacy(n, now, {"destination": "PHX"})[0],
                         "supersede")
        early = datetime(2025, 11, 25, tzinfo=CDT)
        self.assertEqual(review_legacy(n, early)[0], "keep")


class TestVerify(unittest.TestCase):
    def test_reconciler_passes_wrong_city(self):
        prop = {"flight": "XPA0842", "destination": "DEN"}
        self.assertTrue(pnr_reconciler(prop, dict(prop)))
        self.assertEqual(destination_verifier(IT, prop),
                         "wrong-destination")

    def test_requested_change_goes_to_desk(self):
        a = {"flight": "XPA0842", "destination": "DEN"}
        self.assertEqual(destination_verifier(IT, a, "DEN"), "desk")

    def test_month(self):
        pnr_ok, dest_ok, wrong = demo.outcomes(T)
        self.assertEqual((pnr_ok, dest_ok, wrong), (1020, 982, 38))


class TestPacket(unittest.TestCase):
    def test_pilot_pins_the_note(self):
        a = packet(IT, "pilot")
        slots = [s for s, _ in where(a, "prefers Denver")]
        self.assertEqual(slots, ["memory", "pinned"])
        self.assertEqual([s for s, _ in where(a, "PHX")], ["task"])
        self.assertEqual(replay_choice(IT, a)[0], "XPA0842")

    def test_fixed_has_record_not_note(self):
        a = packet(IT, "fixed")
        self.assertEqual(where(a, "prefers Denver"), [])
        self.assertEqual(fixed_choice(IT, a)[0], "XPA1422")

    def test_replay_counts(self):
        out = io.StringIO()
        with redirect_stdout(out):
            demo.show_replay(T)
        self.assertIn("PHX 0, DEN 41", out.getvalue())
        self.assertIn("PHX 41, DEN 0", out.getvalue())


class TestWeekly(unittest.TestCase):
    def test_sample_size_and_dates(self):
        w = date(2026, 5, 4)
        s = fresh_sample(w)
        self.assertEqual(len(s), 200)
        self.assertTrue(all(w <= q.as_of <= date(2026, 5, 10) for q in s))

    def test_golden_predates_build(self):
        self.assertTrue(all(q.as_of <= date(2026, 5, 20)
                            for q in golden()))

    def test_nightly_alerts_contract_quiet(self):
        nightly = [r["week"] for r in run("nightly") if r["alert"]]
        self.assertEqual(nightly, [date(2026, 5, 4), date(2026, 6, 1)])
        self.assertFalse(any(r["alert"] for r in run("contract")))

    def test_golden_flat_under_frozen(self):
        rows = run("frozen")
        self.assertEqual(len({round(r["golden"], 3) for r in rows}), 1)
        self.assertGreater(max(r["gap"] for r in rows), 10)


class TestDemo(unittest.TestCase):
    def test_lines_fit(self):
        for argv in ([], ["--no-verifier"], ["--ttl", "365"]):
            out = io.StringIO()
            with redirect_stdout(out):
                demo.main(argv)
            self.assertEqual(too_long(out.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
