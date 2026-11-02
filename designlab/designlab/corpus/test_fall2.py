"""Tests for corpus.fall2, the May 19, 2026 cancellation."""
from __future__ import annotations

import unittest
from collections import Counter

from corpus.fall2 import (CHECKED_IN, CITY, FALL2_TABLES, N_ACCOUNT,
                          N_HELD, N_ITINS, N_REBOOKED, N_REFUND,
                          N_REFUSAL, N_WRONG, NOTE_ID, WRONG,
                          fall2_digest, generate_fall2, note_expiry)

# Changing corpus/fall2.py changes this digest; the chapter quotes it.
PINNED_FALL2_DIGEST = (
    "630ce76fda3b3176a46407d553b157a2f92e20f72abb896e4e6b84c0aec2c9bb")

T = generate_fall2(2026)


class TestFall2Corpus(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(fall2_digest(T), fall2_digest(generate_fall2(2026)))

    def test_pinned(self):
        self.assertEqual(fall2_digest(T), PINNED_FALL2_DIGEST)

    def test_other_seed_differs(self):
        self.assertNotEqual(fall2_digest(generate_fall2(7)), fall2_digest(T))

    def test_every_table_present(self):
        for name in FALL2_TABLES:
            self.assertTrue(T[name], name)

    def test_counts_exact(self):
        self.assertEqual(len(T["fall2_itins"]), N_ITINS)
        d = Counter(r["disposition"] for r in T["fall2_runs"])
        self.assertEqual(d, {"rebooked": N_REBOOKED,
                             "refund-card": N_REFUND,
                             "refusal": N_REFUSAL})
        acct = [r for r in T["fall2_runs"] if NOTE_ID in r["packet_notes"]]
        self.assertEqual(len(acct), N_ACCOUNT)
        to = Counter((r["disposition"], r["proposal_dest"]) for r in acct)
        self.assertEqual(to, {("rebooked", WRONG): N_WRONG,
                              ("refusal", WRONG): N_HELD})

    def test_everyone_else_to_phoenix(self):
        for r in T["fall2_runs"]:
            if NOTE_ID not in r["packet_notes"] and r["proposal_dest"]:
                self.assertEqual(r["proposal_dest"], CITY)

    def test_fare_limit(self):
        for r in T["fall2_runs"]:
            if r["disposition"] == "rebooked":
                self.assertLessEqual(r["fare_diff_usd"], 250.0)
            if r["disposition"] == "refusal":
                self.assertGreater(r["fare_diff_usd"], 250.0)

    def test_note_expired_the_day_before(self):
        self.assertEqual(note_expiry().isoformat(),
                         "2026-05-18T15:14:09-05:00")
        self.assertFalse(T["fall2_note"][0]["expiry_enforced"])

    def test_recovery(self):
        rec = T["fall2_recovery"]
        self.assertEqual(len(rec), N_WRONG)
        s = Counter(r["status_at_detection"] for r in rec)
        self.assertEqual(s["checked-in"], CHECKED_IN)
        self.assertEqual(max(r["arrived_phx"] for r in rec),
                         "2026-05-20T16:31:00-05:00")
        cost = sum(r["goodwill_usd"] + r["hotel_usd"] + r["onward_usd"]
                   for r in rec)
        self.assertAlmostEqual(cost, 6506.0)

    def test_history_harmless(self):
        for h in T["fall2_history"]:
            self.assertEqual(h["final_dest"], h["itinerary_dest"])
            self.assertFalse(h["pinned"])
            self.assertLess(h["day"], "2026-05-18")

    def test_v0_untouched(self):
        from corpus.fall1 import FALL1_TABLES
        from corpus.generate import TABLES
        for name in FALL2_TABLES:
            self.assertNotIn(name, TABLES)
            self.assertNotIn(name, FALL1_TABLES)


if __name__ == "__main__":
    unittest.main()
