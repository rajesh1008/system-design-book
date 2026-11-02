"""Offline tests for designlab v0. Run: python3 -m unittest ch01.test_ch01"""
from __future__ import annotations

import contextlib
import io
import json
import unittest

from chain.record import ChainRecord, Permission, Proposal, Refused
from common.text import too_long

from . import demo
from .checker import audit
from .v0 import ACTOR, Network, V0Loop, classify_output, demo_shape


def refund_proposal(amount: float = 412.60) -> Proposal:
    return Proposal("refund", "LTG-4471902", amount, "canceled")


class OutputTests(unittest.TestCase):
    def test_plain_text_is_an_answer(self):
        self.assertEqual(classify_output(demo.ANSWER), ("answer", None))

    def test_tool_json_is_an_action(self):
        kind, p = classify_output(demo.REFUND)
        self.assertEqual(kind, "action")
        self.assertEqual((p.itinerary, p.amount_usd),
                         ("LTG-4471902", 412.60))

    def test_unknown_action_is_an_answer(self):
        kind, _ = classify_output('{"action": "wire", "ref": "X", '
                                  '"amount_usd": 5}')
        self.assertEqual(kind, "answer")

    def test_truncated_json_fails_closed(self):
        cut = "```json\n" + demo.REFUND[:-20]
        self.assertEqual(classify_output(cut), ("answer", None))

    def test_prose_around_json_still_parses(self):
        kind, p = classify_output("Sure.\n" + demo.REFUND + "\nDone.")
        self.assertEqual(kind, "action")


class LoopTests(unittest.TestCase):
    def test_one_refund_writes_six_lines_and_one_effect(self):
        t, world = demo.trail(), Network(slow_calls={1})
        rec = V0Loop(world, t).run("r1", demo.REFUND)
        events = [json.loads(x)["event"] for x in t.lines]
        self.assertEqual(events, ["output", "proposal", "permission",
                                  "execution", "verification",
                                  "closed"])
        self.assertEqual(len(world.effects), 1)
        self.assertTrue(rec.verification["ok"])
        self.assertEqual(world.calls, 2)

    def test_execute_without_permission_is_refused_and_trailed(self):
        t, world = demo.trail(), Network()
        rec = ChainRecord(proposal=refund_proposal())
        with self.assertRaises(Refused) as ctx:
            V0Loop(world, t).execute("r2", rec)
        self.assertIn("permission", ctx.exception.missing)
        self.assertEqual(world.effects, [])
        last = json.loads(t.lines[-1])
        self.assertEqual(last["event"], "refused")
        self.assertEqual(last["by"], ACTOR)

    def test_permission_granted_by_the_actor_is_refused(self):
        rec = ChainRecord(proposal=refund_proposal(),
                          permission=Permission("PRM-1", ACTOR, "x",
                                                1500.0),
                          idempotency_key="idem-1")
        world = Network()
        with self.assertRaises(Refused):
            V0Loop(world, demo.trail()).execute("r3", rec)
        self.assertEqual(world.effects, [])

    def test_over_the_limit_goes_to_a_person(self):
        out = demo.REFUND.replace("412.60", "1640.00")
        t, world = demo.trail(), Network()
        rec = V0Loop(world, t).run("r4", out)
        self.assertIsNone(rec.permission)
        self.assertEqual(world.effects, [])
        self.assertEqual(json.loads(t.lines[-1])["event"], "denied")

    def test_an_answer_reaches_nothing(self):
        t, world = demo.trail(), Network()
        V0Loop(world, t).run("r5", demo.ANSWER)
        self.assertEqual((len(t.lines), world.calls), (1, 0))

    def test_demo_shape_duplicates_on_a_late_answer(self):
        t, world = demo.trail(), Network(slow_calls={1})
        demo_shape(world, t, "d1", demo.REFUND)
        self.assertEqual(len(world.effects), 2)


class CheckerTests(unittest.TestCase):
    def run_batch(self, check=True, shape=False, rate=0.02):
        reqs = demo.requests(1000, 7, "refund")
        rng = demo.seeded(7, "ch01", "slow")
        slow = {i for i in range(1, 4000) if rng.random() < rate}
        world, t = Network(slow_calls=slow), demo.trail()
        loop = V0Loop(world, t, check_permission=check)
        for rid, out in reqs:
            if shape:
                demo_shape(world, t, rid, out)
            else:
                loop.run(rid, out)
        return audit(t.lines), world

    def test_v0_has_no_action_without_a_permission_record(self):
        a, world = self.run_batch()
        self.assertGreater(a["acted"], 700)
        self.assertEqual(a["unanswered"],
                         {"allowed": 0, "policy": 0, "once": 0,
                          "verified": 0})
        self.assertEqual(a["verified_ok"], a["acted"])
        refs = [e["ref"] for e in world.effects]
        self.assertEqual(len(refs), len(set(refs)))

    def test_demo_shape_answers_none_of_the_questions(self):
        a, world = self.run_batch(shape=True)
        self.assertEqual(a["unanswered"]["allowed"], a["acted"])
        self.assertEqual(a["unanswered"]["verified"], a["acted"])
        refs = [e["ref"] for e in world.effects]
        self.assertGreater(len(refs), len(set(refs)))

    def test_removing_the_check_loses_permission_but_not_verify(self):
        a, _ = self.run_batch(check=False)
        self.assertEqual(a["unanswered"]["allowed"], a["acted"])
        self.assertLess(a["unanswered"]["verified"], 30)

    def test_edited_trail_line_is_found(self):
        t = demo.trail()
        V0Loop(Network(), t).run("r6", demo.REFUND)
        lines = list(t.lines)
        lines[2] = lines[2].replace("PRM-20931", "PRM-99999")
        self.assertTrue(audit(lines)["links"])
        self.assertEqual(audit(t.lines)["links"], [])


class DemoTests(unittest.TestCase):
    def capture(self, fn, *args, **kw):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            fn(*args, **kw)
        return buf.getvalue()

    def test_lab_output_fits_the_page(self):
        for argv in ([], ["--no-permission-check"],
                     ["--timeout-rate", "0.10"],
                     ["--action", "hotel_cancel"]):
            with self.subTest(argv=argv):
                out = self.capture(demo.main, argv)
                self.assertEqual(too_long(out), [])
                self.assertIn("Refused: permission", out)

    def test_live_path_with_a_scripted_transport(self):
        def scripted(body):
            return {"model": body["model"], "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": demo.REFUND}],
                    "usage": {"input_tokens": 70, "output_tokens": 40}}
        out = self.capture(demo.live, transport=scripted)
        self.assertIn("state=verified", out)
        self.assertEqual(too_long(out), [])


class ClockTests(unittest.TestCase):
    def test_lab_clocks_carry_the_chicago_offset_for_the_day(self):
        from datetime import datetime
        try:
            from zoneinfo import ZoneInfo
            chicago = ZoneInfo("America/Chicago")
        except Exception:  # no time-zone database on this machine
            self.skipTest("time-zone database not available")
        for start in (demo.INCIDENT_START, demo.OCTOBER_START):
            with self.subTest(start=start):
                t = datetime.fromisoformat(start)
                wall = t.replace(tzinfo=None).replace(tzinfo=chicago)
                self.assertEqual(t.utcoffset(), wall.utcoffset())

    def test_trail_lines_carry_the_offset(self):
        t, world = demo.trail(), Network(slow_calls={1})
        V0Loop(world, t).run("req-1", demo.REFUND)
        self.assertTrue(all(json.loads(x)["at"].endswith("-06:00")
                            for x in t.lines))


if __name__ == "__main__":
    unittest.main()
