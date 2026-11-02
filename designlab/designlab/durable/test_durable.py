"""Offline tests for the durable module (stdlib unittest only)."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from .bench import bench
from .demo import incident, wait_week
from .killsuite import lab_spec, rate, run_to_end, suite
from .models import FixtureB, Sampled
from .replay import replay
from .store import PENDING, RunStore
from .workflow import Engine, Kill, SimClock
from .models import FixtureA


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class TestCheckpoint(Base):
    def test_schema_2_holds_pending_fields(self):
        spec = lab_spec()
        eng, ctx, _ = run_to_end(self.base, "durable", spec,
                                 Kill("wait_approval", "commit"),
                                 restarts=0)
        c = sqlite3.connect(self.base / "lab.db")
        schema, body = RunStore(c).latest(spec.run_id)
        self.assertEqual(schema, 2)
        for k in PENDING:
            self.assertIn(k, body)
        self.assertTrue(body["permission_id"].startswith("PRM-"))
        c.close()

    def test_framework_acts_twice_after_refund_kill(self):
        spec = lab_spec()
        eng, ctx, crashes = run_to_end(self.base, "framework", spec,
                                       Kill("refund", "work"))
        self.assertEqual(crashes, 1)
        self.assertEqual(eng.world.credits(spec.itinerary), 2)
        self.assertEqual(len(eng.world.tickets(spec.itinerary)), 2)
        eng.close()


class TestKillSuite(unittest.TestCase):
    def test_durable_resumes_at_every_kill_point(self):
        rows = suite("durable")
        self.assertEqual(len(rows), 24)
        self.assertEqual(rate(rows), 1.0)

    def test_framework_and_memory_do_not(self):
        self.assertLess(rate(suite("framework")), 1.0)
        self.assertLess(rate(suite("memory")), rate(suite("framework")))


class TestInjection(Base):
    def stripped(self, lose_journal=False):
        spec = lab_spec()
        eng, _, _ = run_to_end(self.base, "durable", spec,
                               Kill("wait_approval", "commit"), restarts=0)
        eng.close()
        c = sqlite3.connect(self.base / "lab.db")
        RunStore(c).strip_pending(spec.run_id)
        if lose_journal:
            c.execute("delete from journal where seq<=7")
            c.execute("update desk set req_key=null")
            c.commit()
        c.close()
        eng = Engine(self.base, "durable", FixtureA(),
                     SimClock("2026-03-10T13:50:00-05:00"))
        return spec, eng, eng.run(spec.run_id)

    def test_refuses_then_rereads(self):
        spec, eng, ctx = self.stripped()
        self.assertTrue(any(e.startswith("refused to act")
                            for e in ctx.events))
        self.assertTrue(any(e.startswith("re-read PRM-")
                            for e in ctx.events))
        self.assertEqual(ctx.status, "done")
        self.assertEqual(eng.world.count("select count(*) from desk"), 1)
        self.assertEqual(eng.world.credits(spec.itinerary), 1)
        eng.close()

    def test_holds_when_nothing_to_reread(self):
        spec, eng, ctx = self.stripped(lose_journal=True)
        self.assertEqual(ctx.status, "held for a person")
        self.assertEqual(eng.world.tickets(spec.itinerary), [])
        self.assertEqual(eng.world.count("select count(*) from desk"), 1)
        eng.close()


class TestReplay(Base):
    def setUp(self):
        super().setUp()
        self.spec = lab_spec()
        eng, _, _ = run_to_end(self.base, "durable", self.spec, Kill())
        eng.close()
        self.c = sqlite3.connect(self.base / "lab.db")

    def tearDown(self):
        self.c.close()
        super().tearDown()

    def test_strict_replay_calls_nothing(self):
        before = self.c.execute("select count(*) from airline").fetchone()
        r = replay(self.c, self.spec.run_id)
        self.assertIsNone(r.divergence)
        self.assertEqual((r.steps, r.model_calls), (12, 0))
        after = self.c.execute("select count(*) from airline").fetchone()
        self.assertEqual(before, after)

    def test_other_model_flags_first_divergence(self):
        r = replay(self.c, self.spec.run_id, model=FixtureB())
        self.assertEqual((r.divergence["seq"], r.divergence["step"]),
                         (4, "model_choose"))

    def test_replay_time(self):
        self.assertLess(bench(200)["p99_ms"], 3000)


class TestTimers(Base):
    def test_timer_fires_once(self):
        c = sqlite3.connect(self.base / "t.db")
        s = RunStore(c)
        clock = SimClock("2026-03-10T14:00:00-05:00")
        s.set_timer("RUN-1", "escalate", clock.now())
        self.assertTrue(s.fire("RUN-1", "escalate"))
        self.assertFalse(s.fire("RUN-1", "escalate"))
        c.close()

    def test_week_long_wait(self):
        o = wait_week("durable")
        self.assertEqual(o["requests"], 1)
        self.assertEqual(o["decision"], "approved")
        self.assertIn("escalate", o["fired"])
        self.assertNotIn("deadline", o["fired"])
        self.assertGreater(wait_week("framework")["requests"], 20)

    def test_no_answer_takes_the_none_path(self):
        o = wait_week("durable", answer=False)
        self.assertEqual(o["decision"], "expired")


class TestIncident(Base):
    def test_march_restart(self):
        d = incident("durable", self.base, Sampled(0.55))
        self.assertEqual((d["requests"], d["orphaned"], d["timers"]),
                         (9, 0, 9))
        with tempfile.TemporaryDirectory() as other:
            f = incident("framework", Path(other), Sampled(0.55))
        self.assertEqual((f["requests"], f["orphaned"], f["timers"]),
                         (18, 3, 0))
        self.assertEqual(f["two_offers"], 1)
        self.assertEqual(d["dup_credits"] + f["dup_credits"], 0)


if __name__ == "__main__":
    unittest.main()
