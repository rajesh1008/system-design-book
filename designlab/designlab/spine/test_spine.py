"""Chapter 8 tests: ordering, backpressure, dead letters, fan-out.

Offline and seeded. The ordering test is the depth-rule number: 0
out-of-order applications in 100,000 shuffled events.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from spine import backpressure as bp
from spine.deadletter import Consumer, parse_v2
from spine.fanout import fan_out, itineraries, summary
from spine.inbox import Inbox
from spine.order import (Event, SequenceGuard, coalesce, partition_for,
                         trial)

SEED = 8
ROOT = Path(__file__).resolve().parent.parent


class Ordering(unittest.TestCase):
    def test_same_key_same_partition(self):
        for n in (4, 16, 64):
            self.assertEqual(partition_for("LTG-1", n),
                             partition_for("LTG-1", n))

    def test_stale_event_is_rejected(self):
        g = SequenceGuard()
        g.apply(Event("K", 42, "b"))
        self.assertEqual(g.apply(Event("K", 41, "a")), "stale")
        self.assertEqual(g.state["K"], 42)

    def test_zero_out_of_order_in_100k_shuffled(self):
        r = trial(SEED, 100_000)
        self.assertEqual(r["shuffled"]["delivered"], 100_000)
        self.assertGreater(r["shuffled"]["out_of_order"], 0)
        self.assertGreater(r["partitioned"]["out_of_order"], 0)
        self.assertEqual(r["guarded"]["out_of_order"], 0)
        self.assertEqual(r["guarded"]["wrong_final"], 0)

    def test_coalesce_keeps_newest(self):
        evs = [Event("K", s, str(s)) for s in (3, 1, 6, 2)]
        self.assertEqual([e.seq for e in coalesce(evs)], [6])


class Inboxes(unittest.TestCase):
    def test_duplicate_and_stale(self):
        ib = Inbox("t")
        self.assertEqual(ib.handle("m1", "K", 2, "x"), "applied")
        self.assertEqual(ib.handle("m1", "K", 2, "x"), "duplicate")
        self.assertEqual(ib.handle("m0", "K", 1, "old"), "stale")
        self.assertEqual(ib.seq("K"), 2)


class Backpressure(unittest.TestCase):
    def arrivals(self):
        cmds = fan_out("CXL-0201", itineraries(SEED))
        return [int(c.at_s) for c in cmds if c.queue == "approvals"]

    def test_cap_is_derived(self):
        self.assertEqual(bp.cap_for(6, 80, 660), 50)

    def test_cap_holds_and_never_drops(self):
        r = bp.desk(self.arrivals(), cap=50, seed=SEED)
        self.assertLessEqual(r.peak_pending, 50)
        self.assertEqual(r.dropped, 0)
        self.assertEqual(r.decided, 400)
        self.assertEqual(r.stale_on_review, 0)
        self.assertLess(bp.sampled_peak(r), 12 * 60)

    def test_no_cap_serves_stale_cards(self):
        r = bp.desk(self.arrivals(), cap=None, seed=SEED)
        self.assertGreater(r.stale_on_review, 300)

    def test_alert_and_reserve_keep_the_promise(self):
        r = bp.desk(self.arrivals(), cap=50, reserve=4, seed=SEED)
        self.assertIsNotNone(r.alert_s)
        self.assertLess(r.alert_s, 60)
        self.assertLess(r.last_decision_s, 3600)

    def test_admit_only_lowers(self):
        s = bp.Signals(38, 50, 0.07, 0.05, 31.0, 120.0)
        self.assertEqual(bp.admit(40, s), (6, "supplier throttling"))
        s = bp.Signals(0, 50, 0.0, 0.05, 120.0, 120.0)
        self.assertEqual(bp.admit(40, s)[0], 0)


class DeadLetters(unittest.TestCase):
    def msg(self, i, key, seq, dep):
        return json.dumps({"id": i, "key": key, "seq": seq,
                           "dep": dep}).encode()

    def test_poison_parks_only_its_itinerary(self):
        c = Consumer("s", owner="o")
        bad = self.msg("b", "K1", 1, "2026-02-01T18:40:00")
        self.assertEqual(c.offer(bad), "dead-lettered")
        late = self.msg("c", "K1", 2, "2026-02-01T19:00:00-07:00")
        self.assertEqual(c.offer(late), "parked")
        other = self.msg("d", "K2", 1, "2026-02-01T19:00:00-07:00")
        self.assertEqual(c.offer(other), "applied")
        self.assertEqual(c.letters["K1"].raw, bad)

    def test_transient_retries_then_quarantines(self):
        c = Consumer("s", owner="o", max_attempts=5)
        m = self.msg("a", "K", 1, "2026-02-01T18:40:00-07:00")
        self.assertEqual(c.offer(m, flaky=4), "applied")
        m2 = self.msg("b", "K2", 1, "2026-02-01T18:40:00-07:00")
        self.assertEqual(c.offer(m2, flaky=9), "dead-lettered")
        self.assertEqual(c.letters["K2"].attempts, 5)

    def test_replay_in_order_and_idempotent(self):
        c = Consumer("s", owner="o")
        c.offer(self.msg("b", "K", 1, "2026-02-01T18:40:00"))
        c.offer(self.msg("c", "K", 2, "2026-02-01T19:00:00-07:00"))
        self.assertEqual(c.replay("K", parse_v2),
                         ["applied", "applied"])
        self.assertEqual(c.inbox.seq("K"), 2)
        again = c.offer(self.msg("c", "K", 2, "x-07:00"))
        self.assertEqual(again, "duplicate")


class FanOut(unittest.TestCase):
    def test_three_queues_and_counts(self):
        s = summary(fan_out("CXL-0201", itineraries(SEED)))
        self.assertEqual(s["total"], 3900)
        self.assertEqual(s["per"]["approvals"], 400)
        self.assertEqual(s["first_min"]["approvals"], 400)

    def test_redelivered_event_adds_nothing(self):
        rows = itineraries(SEED)
        ib = Inbox("p")
        from spine.fanout import deliver
        deliver(fan_out("E", rows), ib)
        again = deliver(fan_out("E", rows), ib)
        self.assertEqual(again["duplicate"], 3900)
        self.assertEqual(ib.count(), 3900)


class Demo(unittest.TestCase):
    def test_demo_runs_offline_and_fits_70(self):
        env = dict(os.environ, DESIGNLAB_OFFLINE="1")
        env.pop("ANTHROPIC_API_KEY", None)
        r = subprocess.run([sys.executable, "-m", "spine.demo"],
                           cwd=ROOT, env=env, capture_output=True,
                           text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr[-400:])
        long = [ln for ln in r.stdout.splitlines() if len(ln) > 70]
        self.assertEqual(long, [])


if __name__ == "__main__":
    unittest.main()
