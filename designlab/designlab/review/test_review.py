"""Offline tests for the review package (Chapter 42)."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import date

from common.text import too_long

from review import board, checklist, gaps
from review.demo import main
from review.log import by_month, card, load_log
from review.record import MINUTES, Option, Record, validate
from review.store import load_store
from review.submission import apply_conditions, inject, load

V1, V2 = load("points-transfer-v1"), load("points-transfer-v2")


def failing(sub):
    return {r.item.id for r in checklist.run(sub) if not r.passed}


class Checklist(unittest.TestCase):
    def test_sixteen_items_four_per_plane(self):
        planes = [i.plane for i in checklist.ITEMS]
        self.assertEqual(len(planes), 16)
        for p in ("action", "control", "knowledge", "trail"):
            self.assertEqual(planes.count(p), 4)

    def test_shape_items_are_blocking(self):
        for i in checklist.ITEMS:
            if i.shape:
                self.assertTrue(i.blocking, i.id)

    def test_v1_fails_eight(self):
        self.assertEqual(failing(V1), {"A2", "A3", "C2", "C4", "K1",
                                       "T1", "T3", "T4"})

    def test_v2_fails_two(self):
        self.assertEqual(failing(V2), {"K1", "T3"})

    def test_key_signed_after_first_review(self):
        self.assertNotIn("usecase.transfer",
                         checklist.signed_keys(date(2026, 9, 3)))
        self.assertEqual(
            checklist.signed_keys(date(2026, 9, 8))["usecase.transfer"],
            "Rachel Morgan")


class Verdicts(unittest.TestCase):
    def test_v1_declined(self):
        v = board.decide(V1)
        self.assertEqual(v.outcome, "decline")
        self.assertEqual(v.shape, ("A2", "T1"))
        self.assertFalse(v.may_ship)

    def test_v2_changed_and_may_ship(self):
        v = board.decide(V2)
        self.assertEqual(v.outcome, "change")
        self.assertTrue(v.may_ship)

    def test_self_verify_declines(self):
        v = board.decide(inject(V2, "self-verify"))
        self.assertEqual(v.outcome, "decline")
        self.assertEqual(v.shape, ("T1",))

    def test_no_kill_switch_blocks_without_decline(self):
        v = board.decide(inject(V2, "no-kill-switch"))
        self.assertEqual(v.outcome, "change")
        self.assertEqual(v.blocking, ("C3",))
        self.assertFalse(v.may_ship)

    def test_no_stop_declines(self):
        v = board.decide(inject(V2, "no-stop"))
        self.assertEqual(v.shape, ("A2",))

    def test_conditions_close_the_change(self):
        v = board.decide(apply_conditions(V2))
        self.assertEqual((v.outcome, v.passed), ("approve", 16))

    def test_inject_leaves_original(self):
        inject(V2, "self-verify")
        self.assertEqual(failing(V2), {"K1", "T3"})

    def test_reader_reading_actor_output_fails_t2(self):
        s = V2.copy()
        s.diagram["edges"].append({"from": "ledger", "to": "recon",
                                   "kind": "data", "label": "receipt"})
        self.assertIn("T2", failing(s))


class Gaps(unittest.TestCase):
    def test_five_questions_cover_gap_items(self):
        self.assertEqual([g[0] for g in gaps.GAPS],
                         ["G1", "G2", "G3", "G4", "G5"])

    def test_v1_answers_one(self):
        self.assertEqual(sum(ok for _, _, ok, _ in gaps.walk(V1)), 1)

    def test_v2_answers_four(self):
        self.assertEqual(sum(ok for _, _, ok, _ in gaps.walk(V2)), 4)


class Records(unittest.TestCase):
    def test_minutes_refused(self):
        self.assertEqual(len(validate(MINUTES)), 6)

    def test_signer_must_differ(self):
        r = Record(id="x", review="", title="t", date="2026-09-08",
                   owner="A", signer="A", context="c",
                   options=[Option("a", True), Option("b", False, "n")],
                   decision="d", evidence=["e"], consequences=["k"],
                   revisit_date="2026-12-08", revisit_trigger="t")
        self.assertEqual(validate(r),
                         ["REC-SIG signer missing or same as owner"])

    def test_losing_option_needs_reason(self):
        r = load_store().get("DR-42.1")
        r.options[1].why_not = ""
        self.assertTrue(any("no reason" in p for p in validate(r)))

    def test_store_all_valid(self):
        s = load_store()
        self.assertEqual(len(s.all()), 14)
        self.assertEqual(s.invalid(), {})
        self.assertEqual(len(s.revisited()), 3)
        self.assertEqual([r.id for r in s.due(date(2026, 9, 8))],
                         ["RR-02"])


class Card(unittest.TestCase):
    def test_card(self):
        c = card(load_log())
        self.assertEqual((c["designs reviewed"], c["declined"],
                          c["changed"], c["approved as submitted"]),
                         (14, 2, 9, 3))
        self.assertEqual(c["shipped without a kill switch"], 0)
        self.assertEqual(c["records"], 14)
        self.assertEqual(c["reviews with no record"], 0)

    def test_months(self):
        m = by_month(load_log())
        self.assertEqual(sum(sum(c.values()) for c in m.values()), 14)
        self.assertEqual(m["2026-06"]["change"], 5)

    def test_every_logged_record_in_store(self):
        s = load_store()
        for e in load_log():
            self.assertIsNotNone(s.get(e.record), e.id)


class Demo(unittest.TestCase):
    def test_demo_fits_width(self):
        for argv in ([], ["--part", "verdict", "--inject",
                          "self-verify"],
                     ["--part", "checklist", "--design",
                      "points-transfer-v2"]):
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(main(argv), 0)
            self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
