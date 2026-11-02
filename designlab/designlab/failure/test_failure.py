"""Tests for the failure package (Chapter 12). Offline."""
from __future__ import annotations

import contextlib
import io
import random
import sys
import unittest

from corpus.fall1 import generate_fall1, hms, most_slow_at
from failure.batch import (replay_fixed, replay_injected,
                           starts_while_open)
from failure.breaker import Breaker
from failure.catalog import CATALOG, by_plane
from failure.degrade import HoldQueue, rung
from failure.reconcile import (extra_credits, interval_scan, ratio_alert,
                               reconcile)
from failure.retry import (POLICIES, RetryBudget, amplification, backoff,
                           policy)

F = generate_fall1(2026)
REFUNDS = F["fall1_refunds"]
INJ = replay_injected(F)
FIX = replay_fixed(F)


def report(run):
    return reconcile(run.lines(), run.owed(REFUNDS),
                     set(run.ledger.entries))


def line(charge, at, ref="k", amount=10.0):
    return {"charge_id": charge, "at": at, "ref": ref,
            "amount_usd": amount}


class TestCatalogAndRetry(unittest.TestCase):
    def test_every_plane_listed(self):
        self.assertEqual(set(by_plane()), {"action", "control",
                                           "knowledge", "trail",
                                           "outside"})
        self.assertEqual(len(CATALOG), 16)

    def test_unkeyed_effect_never_retried(self):
        self.assertEqual(policy("effect, no key").attempts, 1)
        for p in POLICIES:
            if p.attempts > 1:
                self.assertIn(p.key, ("read", "ledger key"))

    def test_amplification(self):
        self.assertEqual(amplification(5, 3), 243)

    def test_backoff_capped(self):
        rng = random.Random(1)
        for n in range(1, 10):
            self.assertLessEqual(backoff(n, 1.0, 8.0, rng), 8.0)

    def test_budget(self):
        b = RetryBudget(size=2)
        self.assertEqual([b.may_retry() for _ in range(3)],
                         [True, True, False])


class TestBreaker(unittest.TestCase):
    def test_trips_on_slow_window(self):
        b = Breaker(min_calls=4, trip_share=0.5)
        for i in range(3):
            b.record(i, 5.0, True)
        self.assertEqual(b.state, "closed")   # below min_calls
        b.record(3, 5.0, True)
        self.assertEqual(b.state, "open")
        self.assertFalse(b.allows_effect(3))

    def test_fast_calls_keep_it_closed(self):
        b = Breaker()
        for i in range(50):
            b.record(i, 1.0, True)
        self.assertEqual(b.state, "closed")

    def test_half_open_probes(self):
        b = Breaker(min_calls=1, open_s=10)
        b.record(0, 0, False)
        self.assertFalse(b.due_probe(5))
        self.assertTrue(b.due_probe(10))
        self.assertFalse(b.allows_effect(10))  # probes only
        b.probe(10, 3.0)
        self.assertEqual(b.state, "open")      # bad probe
        b.due_probe(20)
        b.probe(20, 1.0)
        b.probe(25, 1.0)
        self.assertEqual(b.state, "closed")


class TestDegrade(unittest.TestCase):
    def test_ladder(self):
        self.assertEqual(rung(), "full")
        self.assertEqual(rung(breaker_open=True), "propose-only")
        self.assertEqual(rung(kill_tier=2), "propose-only")
        self.assertEqual(rung(control_down=True), "answer-only")
        self.assertEqual(rung(kill_tier=3), "people-only")

    def test_queue_paced(self):
        q = HoldQueue()
        for t in range(4):
            q.hold(t, t)
        out = q.release(10, per_s=2)
        self.assertEqual([t for t, _ in out], [10, 10.5, 11, 11.5])
        self.assertEqual(q.waits, [10, 9.5, 9, 8.5])


class TestReconcile(unittest.TestCase):
    def test_counts(self):
        lines = [line("A", 1), line("A", 2), line("B", 3, ref="x")]
        r = reconcile(lines, {"A": 10, "B": 10, "C": 10}, {"k"})
        self.assertEqual((r.duplicates, r.missing, r.orphans), (1, 1, 1))

    def test_ratio_and_scan(self):
        lines = [line("A", 10), line("A", 20), line("B", 30)]
        row = ratio_alert(lines, [150], window_s=100, cut_s=50)[0]
        self.assertTrue(row["fired"])
        s = interval_scan(lines, 15, 0, 100)
        self.assertEqual((s["flag_at"], s["paid_before"]), (30, 1))


class TestTheFall(unittest.TestCase):
    def test_212_duplicates_61000(self):
        r = report(INJ)
        self.assertEqual(r.duplicates, 212)
        self.assertEqual(r.duplicate_usd, 61000.00)
        self.assertEqual((r.paid_twice, r.paid_three), (194, 9))
        self.assertEqual(r.missing, 0)

    def test_all_duplicates_off_gateway(self):
        creds = {x["credential"] for x in extra_credits(INJ.lines())}
        self.assertEqual(creds, {"int-fin-02"})

    def test_window(self):
        ex = extra_credits(INJ.lines())
        self.assertGreaterEqual(ex[0]["at"], hms(15, 10))
        self.assertLess(ex[-1]["at"], hms(15, 50))

    def test_alert_fires_at_352_not_322(self):
        rows = ratio_alert(INJ.lines(), [hms(15, 22), hms(15, 52)])
        self.assertEqual([r["fired"] for r in rows], [False, True])

    def test_reconcile_finds_all_without_ledger(self):
        self.assertEqual(report(INJ).orphans, len(
            [x for x in INJ.lines() if x["credential"] == "int-fin-02"]))


class TestTheFix(unittest.TestCase):
    def test_zero_duplicates(self):
        r = report(FIX)
        self.assertEqual((r.duplicates, r.missing, r.orphans), (0, 0, 0))

    def test_key_per_attempt(self):
        off = replay_fixed(F, mint="attempt", enforce=False)
        on = replay_fixed(F, mint="attempt", enforce=True)
        self.assertEqual(report(off).duplicates, 212)
        self.assertEqual(report(on).duplicates, 0)
        self.assertGreater(on.refused, 0)

    def test_breaker_replay(self):
        b = Breaker()
        run = replay_fixed(F, breaker=b)
        r = report(run)
        self.assertEqual((r.duplicates, r.missing), (0, 0))
        self.assertEqual(starts_while_open(run), 0)
        self.assertLessEqual(b.transitions[0][0] - most_slow_at(), 20)
        self.assertGreater(run.held, 0)


class TestDemo(unittest.TestCase):
    def test_demo_fits_70(self):
        from failure import demo
        buf = io.StringIO()
        argv = sys.argv
        try:
            for extra in ([], ["--part", "tryit", "--mint", "attempt"],
                          ["--part", "tryit", "--every", "15"]):
                sys.argv = ["demo", *extra]
                with contextlib.redirect_stdout(buf):
                    demo.main()
        finally:
            sys.argv = argv
        self.assertTrue(all(len(x) <= 70 for x in
                            buf.getvalue().splitlines()))


if __name__ == "__main__":
    unittest.main()
