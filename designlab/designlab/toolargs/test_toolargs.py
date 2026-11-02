"""Offline tests for the Chapter 16 tool-argument layer."""
import copy
import io
import json
import unittest
from contextlib import redirect_stdout

from common.clock import FixedClock
from common.trail import TrailWriter, check_trail

from toolargs import demo, schema, world
from toolargs.cases import LIVE_CASES, SimProposer, Stream
from toolargs.layer import Intake, Tool, digest
from toolargs.repair import run_call
from toolargs.tools import REBOOK_V2_1, REFUND_V3, TOOLS, api_tool

W = world.build()
GOOD = {"itinerary_id": "LTG-5208841", "ticket_number": "TKT-40218",
        "passenger_name": "OKAFOR/NGOZI", "new_flight_id": "FLT-904452",
        "fare_difference_usd": "318.40", "reason": "voluntary"}
REBOOK = REBOOK_V2_1["input_schema"]


def intake(mode="full", rules=()):
    return Intake(W, TrailWriter(clock=FixedClock()), mode=mode,
                  rules=rules)


class TestSchema(unittest.TestCase):
    def test_good_call_passes(self):
        self.assertEqual(schema.validate(GOOD, REBOOK), [])

    def test_missing_extra_enum_pattern_type(self):
        bad = dict(GOOD)
        del bad["ticket_number"]
        bad["approved"] = True
        bad["reason"] = "Voluntary"
        bad["fare_difference_usd"] = "318.4"
        bad["new_flight_id"] = 904452
        problems = {(e.field, e.problem)
                    for e in schema.validate(bad, REBOOK)}
        self.assertIn(("$.ticket_number", "missing"), problems)
        self.assertIn(("$.approved", "not in the schema"), problems)
        self.assertIn(("$.reason", "not one of the allowed values"),
                      problems)
        self.assertIn(("$.fare_difference_usd",
                       "does not match the format"), problems)
        self.assertIn(("$.new_flight_id", "expected string"), problems)

    def test_numeric_bounds_checked_here(self):
        s = {"type": "integer", "minimum": 0, "maximum": 10}
        self.assertTrue(schema.validate(11, s))
        self.assertTrue(schema.validate(True, s))
        self.assertEqual(schema.validate(10, s), [])

    def test_schemas_avoid_strict_unsupported_keywords(self):
        banned = {"minimum", "maximum", "minLength", "maxLength",
                  "multipleOf", "maxItems"}
        for t in TOOLS.values():
            text = json.dumps(t["input_schema"])
            for k in banned:
                self.assertNotIn(f'"{k}"', text)
            self.assertFalse(t["input_schema"]["additionalProperties"])
            self.assertTrue(api_tool(t)["strict"])


class TestWorld(unittest.TestCase):
    def check(self, **change):
        return W.check("rebook_ticket", dict(GOOD, **change),
                       "LTG-5208841")

    def test_good_call_passes(self):
        self.assertIsNone(self.check())

    def test_the_opening_call_is_rejected(self):
        r = self.check(ticket_number="TKT-40219",
                       passenger_name="OKAFOR/TUNDE")
        self.assertEqual(r.reason, "ticket_not_on_itinerary")
        self.assertEqual(r.field, "ticket_number")

    def test_each_relationship(self):
        cases = {
            "itinerary_not_in_session": {"itinerary_id": "LTG-5208842"},
            "ticket_unknown": {"ticket_number": "TKT-99999"},
            "passenger_not_on_ticket":
                {"passenger_name": "OKAFOR/TUNDE"},
            "flight_unknown": {"new_flight_id": "FLT-999999"},
            "flight_not_on_route": {"new_flight_id": "FLT-904503"},
            "flight_canceled": {"new_flight_id": "FLT-904460"},
            "fare_quote_mismatch": {"fare_difference_usd": "250.00"},
        }
        for reason, change in cases.items():
            with self.subTest(reason):
                self.assertEqual(self.check(**change).reason, reason)

    def test_name_formats(self):
        for n in ("Ngozi Okafor", "okafor/ngozi", " OKAFOR / NGOZI "):
            self.assertIsNone(self.check(passenger_name=n))

    def test_refund_within_fare_left(self):
        base = {"itinerary_id": "LTG-5208850",
                "ticket_number": "TKT-40232", "reason": "goodwill"}
        over = W.check("refund_ticket", dict(base, amount_usd="286.10"),
                       "LTG-5208850")
        self.assertEqual(over.reason, "amount_above_fare_left")
        self.assertIsNone(W.check("refund_ticket",
                                  dict(base, amount_usd="166.10"),
                                  "LTG-5208850"))

    def test_hints_never_name_an_owner(self):
        r = self.check(ticket_number="TKT-40219")
        text = json.dumps(r.as_dict())
        for leak in ("TUNDE", "LTG-5208842", "OKAFOR", "TKT-40219"):
            self.assertNotIn(leak, text)
        self.assertEqual(set(world.HINTS), set(world.REASONS))

    def test_cross_field_rule(self):
        args = {"itinerary_id": "LTG-5208850",
                "ticket_number": "TKT-40231", "amount_usd": "20.00",
                "reason": "canceled_by_carrier"}
        self.assertIsNone(W.check("refund_ticket", args, "LTG-5208850"))
        r = W.check("refund_ticket", args, "LTG-5208850",
                    (world.rule_reason_in_record,))
        self.assertEqual(r.reason, "reason_not_in_record")


class TestIntake(unittest.TestCase):
    def test_digest_binds_every_argument(self):
        d = digest("rebook_ticket", GOOD)
        self.assertEqual(d, digest("rebook_ticket", dict(GOOD)))
        for k in GOOD:
            changed = dict(GOOD, **{k: GOOD[k] + "x"})
            self.assertNotEqual(d, digest("rebook_ticket", changed))

    def test_schema_only_lets_world_errors_through(self):
        bad = dict(GOOD, ticket_number="TKT-40219")
        self.assertTrue(intake("schema-only").check(
            "LTG-5208841", "rebook_ticket", bad).ok)
        v = intake().check("LTG-5208841", "rebook_ticket", bad)
        self.assertFalse(v.ok)
        self.assertEqual(v.stage, "world")

    def test_errors_for_the_model(self):
        v = intake().check("LTG-5208841", "rebook_ticket",
                           dict(GOOD, fare_difference_usd="250.00"))
        self.assertEqual(v.for_model(1, bare=True),
                         {"error": "invalid request"})
        m = v.for_model(1)
        self.assertEqual(m["errors"][0]["field"], "fare_difference_usd")
        self.assertEqual(m["repairs_left"], 1)

    def test_unknown_tool_is_a_schema_rejection(self):
        v = intake().check("LTG-5208841", "reissue_ticket", GOOD)
        self.assertEqual(v.stage, "schema")


class Stub:
    """A proposer that returns a scripted list of argument sets."""

    def __init__(self, script):
        self.script = [copy.deepcopy(s) for s in script]

    def first(self, case):
        return self.script.pop(0)

    def repair(self, case, args, feedback):
        return self.script.pop(0) if self.script else copy.deepcopy(args)


class C:
    n, session, tool = 0, "LTG-5208841", "rebook_ticket"


class TestRepair(unittest.TestCase):
    bad1 = dict(GOOD, ticket_number="TKT-40219")
    bad2 = dict(GOOD, fare_difference_usd="250.00")
    bad3 = dict(GOOD, new_flight_id="FLT-904460")

    def test_repaired_on_second_attempt(self):
        o = run_call(Stub([self.bad1, self.bad2, GOOD]), C, intake(),
                     Tool(W))
        self.assertEqual((o.status, o.repairs), ("repaired", 2))

    def test_budget_hands_off(self):
        o = run_call(Stub([self.bad1, self.bad2, self.bad3, GOOD]), C,
                     intake(), Tool(W))
        self.assertEqual((o.status, o.why, o.model_calls),
                         ("handed_off", "budget", 3))

    def test_no_progress_hands_off_at_once(self):
        o = run_call(Stub([self.bad1, self.bad1]), C, intake(), Tool(W))
        self.assertEqual((o.status, o.why, o.repairs),
                         ("handed_off", "no_progress", 1))

    def test_unbounded_keeps_going(self):
        script = [self.bad1, self.bad2] * 5 + [GOOD]
        o = run_call(Stub(script), C, intake(), Tool(W), budget=None,
                     bare=True)
        self.assertEqual((o.status, o.repairs), ("repaired", 10))

    def test_tool_never_sees_a_rejected_call(self):
        i, t = intake(), Tool(W)
        run_call(Stub([self.bad1, self.bad2, self.bad3]), C, i, t)
        self.assertEqual((t.received, t.rejected_by_intake), (0, 0))


class TestDemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = {}
        for key, argv in {
                "full": ["--seed", "16"],
                "schema": ["--seed", "16", "--inject", "schema-only"],
                "loop": ["--seed", "16", "--inject", "unbounded-repair"],
                "okafor": ["--case", "okafor"],
                "tools": ["--case", "tools"],
                "verdict": ["--case", "verdict"]}.items():
            buf = io.StringIO()
            with redirect_stdout(buf):
                demo.main(argv)
            cls.out[key] = buf.getvalue()

    def test_headline_numbers(self):
        out = self.out["full"]
        self.assertIn("100.0%", out)
        self.assertRegex(out, r"world-rejected on first proposal +\d+ +"
                              r"2\.1%")
        self.assertRegex(out, r"repaired within two attempts +\d+ +"
                              r"94\.0%")
        self.assertRegex(out, r"handed off to the agent desk +\d+ +"
                              r"6\.0%")
        self.assertRegex(out, r"world-invalid calls that reached a tool"
                              r" +0\n")
        self.assertIn("chain intact", out)

    def test_schema_only_reaches_the_tool(self):
        out = self.out["schema"]
        n = int(out.split("world-invalid calls that reached a tool")[1]
                .split()[0])
        self.assertGreater(n, 300)
        self.assertIn("another passenger ticket reissued", out)

    def test_unbounded_loops(self):
        out = self.out["loop"]
        most = int(out.split("most repairs on one call")[1].split()[0])
        self.assertGreaterEqual(most, 11)

    def test_okafor(self):
        out = self.out["okafor"]
        self.assertIn("schema check      pass", out)
        self.assertIn("world check       ticket_not_on_itinerary", out)

    def test_tools_and_verdict(self):
        self.assertIn("rebook_ticket 2.1  strict=True  closed=True",
                      self.out["tools"])
        out = self.out["verdict"]
        self.assertIn("{'error': 'invalid request'}", out)
        self.assertIn("reason: ticket_not_on_itinerary", out)
        self.assertNotIn("OKAFOR/TUNDE", out)

    def test_lines_fit(self):
        for text in self.out.values():
            for line in text.splitlines():
                self.assertLessEqual(len(line), 70, line)

    def test_live_cases_shape(self):
        self.assertEqual(len(LIVE_CASES), 20)
        self.assertGreaterEqual(sum(c.trap for c in LIVE_CASES), 10)


if __name__ == "__main__":
    unittest.main()
