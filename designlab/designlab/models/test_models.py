"""Offline tests for Chapter 13's model contracts. No key, no network."""
from __future__ import annotations

import contextlib
import dataclasses
import io
import json
import unittest
from pathlib import Path

from common.client import FixtureTransport
from common.redact import find_secrets
from common.spend import SpendMeter

from . import demo, variance
from .contract import (check, check_output, load_contract, load_contracts,
                       parse_json)
from .drift import (EchoAs, LoudMove, SilentMove, baseline, compare,
                    lenient_last_object, lenient_reason)
from .fares import cents, unflown_refund_cents, usd
from .record import ARCHIVE, FIX, alias_contract
from .runner import client_for, golden_cases, guarded_call, run_suite

HERE = Path(__file__).resolve().parent


class Done:
    def __init__(self, text, model="claude-haiku-5-5", stop="end_turn"):
        self.text, self.model, self.stop_reason = text, model, stop
        self.cost_usd = 0.0


def rr():
    return load_contracts()["refund-reason"]


def ok_reason(**over):
    d = {"reason_code": "carrier_canceled",
         "evidence": "the airline canceled my flight", "needs_person": False}
    d.update(over)
    return json.dumps(d)


MSG = {"message": "Hi, the airline canceled my flight to Denver."}


class ContractFiles(unittest.TestCase):
    def test_three_contracts_load_with_owners_and_dates(self):
        cs = load_contracts()
        self.assertEqual(sorted(cs), ["change-intent", "desk-note",
                                      "refund-reason"])
        for c in cs.values():
            self.assertTrue(c.owner and c.alert_to)
            self.assertLess(c.review_by, c.retire_not_before)
            self.assertEqual(c.id_kind, "snapshot")
            self.assertEqual(c.expect_echo, c.model_id)

    def test_no_contract_lets_the_model_state_an_amount(self):
        for c in load_contracts().values():
            self.assertIn("amount", c.forbidden_fields)
            self.assertNotIn("amount", c.field_names())

    def test_prompt_hash_changes_with_the_prompt(self):
        c = rr()
        c2 = dataclasses.replace(c, system=c.system + " ")
        self.assertNotEqual(c.prompt_hash, c2.prompt_hash)
        self.assertEqual(len(c.prompt_hash), 12)

    def test_review_after_retirement_is_rejected(self, tmp=None):
        src = (HERE / "contracts" / "refund-reason.toml").read_text()
        bad = src.replace('review_by = "2027-07-09"',
                          'review_by = "2027-12-01"')
        p = Path("/tmp/ch13-bad-contract.toml")
        p.write_text(bad)
        with self.assertRaises(ValueError):
            load_contract(p)

    def test_schema_for_constrained_decoding(self):
        s = load_contracts()["desk-note"].json_schema()
        self.assertFalse(s["additionalProperties"])
        self.assertEqual(set(s["required"]),
                         {"itinerary_ref", "asks_for", "note"})
        self.assertIn("enum", s["properties"]["asks_for"])
        self.assertNotIn("maxLength", json.dumps(s))  # checked, not sent


class OutputChecks(unittest.TestCase):
    def codes(self, text, inputs=MSG, **kw):
        return [v.code for v in check(rr(), Done(text, **kw), inputs)]

    def test_good_output_passes(self):
        self.assertEqual(self.codes(ok_reason()), [])

    def test_each_violation_has_its_own_code(self):
        self.assertEqual(self.codes("Sure. The reason is a cancel."),
                         ["not-json"])
        self.assertIn("forbidden-field",
                      self.codes(ok_reason(refund_amount="900.00")))
        self.assertIn("extra-field", self.codes(ok_reason(confidence=0.9)))
        self.assertIn("bad-enum",
                      self.codes(ok_reason(reason_code="Carrier Canceled")))
        self.assertIn("bad-type",
                      self.codes(ok_reason(needs_person="no")))
        self.assertIn("not-quoted",
                      self.codes(ok_reason(evidence="flight was scrapped")))
        d = json.loads(ok_reason())
        del d["needs_person"]
        self.assertIn("missing-field", self.codes(json.dumps(d)))

    def test_echo_truncation_and_refusal(self):
        self.assertIn("echo-drift",
                      self.codes(ok_reason(), model="claude-haiku-6-0"))
        self.assertIn("truncated", self.codes('{"reason_code": "car',
                                              stop="max_tokens"))
        self.assertEqual(self.codes("", stop="refusal"), ["refusal"])

    def test_fenced_json_is_accepted_two_objects_are_not(self):
        self.assertIsNotNone(parse_json("```json\n" + ok_reason() + "\n```"))
        self.assertIsNone(parse_json(ok_reason() + "\n" + ok_reason()))

    def test_desk_note_may_not_state_money(self):
        c = load_contracts()["desk-note"]
        facts = {"facts": "itinerary LTG-4471902; refund 412.60"}
        note = {"itinerary_ref": "LTG-4471902", "asks_for": "approve_refund"}
        for bad in ("Refund $412.60 now.", "Refund 412.60 now.",
                    "About 400 dollars."):
            v = check_output(c, {**note, "note": bad}, facts)
            self.assertIn("forbidden-text", [x.code for x in v])
        v = check_output(c, {**note, "note": "Unflown return leg; amount "
                                         "per fare tool."}, facts)
        self.assertEqual(v, [])


class Fixtures(unittest.TestCase):
    def test_current_suites_pass_offline(self):
        for name, c in load_contracts().items():
            r = run_suite(c, FixtureTransport(FIX / name))
            self.assertTrue(r.ok(), name)
            self.assertEqual(r.passed, len(golden_cases(c)))

    def test_archived_versions_fail_as_recorded(self):
        c = load_contract(ARCHIVE / "refund-reason-1.2.toml")
        r = run_suite(c, FixtureTransport(FIX / "refund-reason-1.2"))
        self.assertEqual([x.case_id for x in r.cases if not x.passed],
                         ["rr-05"])
        c = load_contract(ARCHIVE / "desk-note-2.1.toml")
        r = run_suite(c, FixtureTransport(FIX / "desk-note-2.1"))
        self.assertEqual(r.passed, 6)
        loose = [lenient_last_object(x.raw) for x in r.cases]
        self.assertTrue(all(loose))

    def test_no_fixture_holds_a_secret(self):
        files = [p for p in FIX.rglob("*.json")]
        self.assertGreater(len(files), 80)
        for p in files:
            text = p.read_text()
            self.assertEqual(find_secrets(text, fixture=True), [], p.name)
            self.assertNotIn("x-api-key", text)
            self.assertNotIn("sk-ant", text)


class Drift(unittest.TestCase):
    def setUp(self):
        self.c = rr()
        self.t = FixtureTransport(FIX / "refund-reason")
        self.base = baseline(self.c, run_suite(self.c, self.t))

    def alerts(self, wrap, c=None, base=None):
        c = c or self.c
        return [a.code for a in compare(c, base or self.base,
                                        run_suite(c, wrap))]

    def test_unchanged_run_raises_nothing(self):
        self.assertEqual(self.alerts(self.t), [])

    def test_loud_move_is_echo_drift(self):
        self.assertEqual(self.alerts(LoudMove(self.t)), ["echo-drift"])

    def test_silent_move_is_behavior_and_shape(self):
        self.assertEqual(self.alerts(SilentMove(self.t)),
                         ["behavior-drift", "shape-drift"])

    def test_real_alias_move_seen_by_echo_and_by_cost_only(self):
        c = alias_contract()
        base = baseline(c, run_suite(c, FixtureTransport(FIX /
                                                         "alias-before")))
        moved = FixtureTransport(FIX / "alias-moved")
        self.assertEqual(self.alerts(moved, c, base),
                         ["echo-drift", "budget-drift"])
        quiet = EchoAs(moved, base.echo)
        self.assertEqual(self.alerts(quiet, c, base), ["budget-drift"])

    def test_lenient_parser_hides_the_silent_move(self):
        r = run_suite(self.c, SilentMove(self.t))
        mapped = {lenient_reason(self.c, x.raw)[0] for x in r.cases}
        self.assertEqual(mapped, {"other"})


class Repair(unittest.TestCase):
    def fake(self, replies, model="claude-haiku-5-5"):
        def t(body):
            text = replies.pop(0)
            return {"model": model, "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": text}],
                    "usage": {"input_tokens": 300, "output_tokens": 40}}
        return client_for(rr(), t, SpendMeter(cap_usd=0.01))

    def test_one_repair_then_a_person(self):
        g = guarded_call(rr(), self.fake([ok_reason()]), MSG)
        self.assertEqual((g.outcome, g.attempts), ("ok", 1))
        g = guarded_call(rr(), self.fake(["nope", ok_reason()]), MSG)
        self.assertEqual((g.outcome, g.attempts), ("repaired", 2))
        g = guarded_call(rr(), self.fake(["nope", "still no"]), MSG)
        self.assertEqual((g.outcome, g.attempts), ("dead-letter", 2))

    def test_wrong_model_is_never_repaired(self):
        cl = self.fake([ok_reason()], model="claude-haiku-6-0")
        g = guarded_call(rr(), cl, MSG)
        self.assertEqual((g.outcome, g.attempts), ("dead-letter", 1))

    def test_oversized_input_never_reaches_the_model(self):
        g = guarded_call(rr(), self.fake([]), {"message": "x" * 3000})
        self.assertEqual((g.outcome, g.attempts), ("dead-letter", 0))


class Money(unittest.TestCase):
    def test_fare_tool_prorates_in_cents(self):
        self.assertEqual(cents("1,184.30"), 118430)
        self.assertEqual(usd(unflown_refund_cents(
            "1,184.30", "212.48", 1388, 1021, "97.15")), "$509.03")
        self.assertEqual(usd(unflown_refund_cents(
            "2,316.90", "341.62", 712, 2904, "228.40")), "$1,814.74")

    def test_fare_tool_rejects_impossible_inputs(self):
        with self.assertRaises(ValueError):
            unflown_refund_cents("100.00", "120.00", 1, 1, "0.00")

    def test_recorded_model_amounts_are_not_all_the_tool_amount(self):
        _m, s = variance.load(FIX / "variance-amount-small.json")
        got = {(parse_json(x["text"]) or {}).get("refund_amount")
               for x in s if x["case"] == "am-02"}
        self.assertIn("1814.74", got)
        self.assertGreater(len(got), 1)


class Demo(unittest.TestCase):
    def run_demo(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = demo.main(list(argv))
        return code, buf.getvalue()

    def test_every_command_fits_the_page(self):
        for argv in (["contracts"], ["test"], ["format"], ["amount"],
                     ["naive"], ["variance"], ["drift"]):
            code, out = self.run_demo(*argv)
            self.assertEqual(code, 0, argv)
            self.assertTrue(all(len(x) <= 70 for x in out.splitlines()))

    def test_injected_moves_exit_nonzero(self):
        for inj in ("loud", "silent", "alias", "alias-quiet"):
            code, out = self.run_demo("drift", "--inject", inj)
            self.assertEqual(code, 1, inj)
            self.assertIn("ALERT", out)


if __name__ == "__main__":
    unittest.main()
