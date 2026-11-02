"""Offline tests for the Chapter 27 lab. No key, no network."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from common.client import FixtureTransport
from common.redact import find_secrets
from common.spend import SpendMeter
from common.text import MAX_LINE
from effects.ledger import StaleLease

from . import card, compare, demo, handoff, hierarchy, live, lock, vote
from .eligibility import TASKS, Answer, outcome, parse, truth, verify
from .tasks import PER_TYPE, TYPES, golden_set


def _out(*argv) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = demo.main(list(argv))
    return code, buf.getvalue()


class GoldenSet(unittest.TestCase):
    def test_twelve_types_hundred_each(self):
        cases = golden_set()
        self.assertEqual(len(TYPES), 12)
        self.assertEqual(len(cases), 12 * PER_TYPE)
        self.assertEqual(golden_set(), cases)

    def test_hotel_and_car_are_single_leg(self):
        for c in golden_set():
            if c.kind in ("hotel-cancel", "hotel-date-change",
                          "car-rental-change"):
                self.assertEqual(c.legs, 1)


class Compare(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = compare.compare(27)
        cls.t = compare.totals(cls.res)
        cls.r = compare.routed()

    def test_one_agent_wins_nine_of_twelve(self):
        self.assertEqual(self.t["single_wins"], 9)
        self.assertEqual(self.t["ow_wins"], 3)

    def test_orchestrator_wins_only_searching_types(self):
        for kind, r in self.res.items():
            if r.winner in ("orchestrator", "tie-orchestrator"):
                self.assertTrue(TYPES[kind][4], kind)

    def test_orchestrator_costs_more_tokens_overall(self):
        self.assertGreater(self.t["token_ratio"], 1.5)
        self.assertGreater(self.t["coordination_share"], 0.5)

    def test_the_gain_is_on_three_or_more_legs(self):
        few, many = self.r["few"], self.r["many"]
        self.assertGreater(many.ow_ok, many.single_ok)
        self.assertGreater(few.single_ok, few.ow_ok)

    def test_routing_by_legs_beats_either_alone(self):
        self.assertGreater(self.r["routed_ok"], self.r["all_single_ok"])
        self.assertGreater(self.r["routed_ok"], self.r["all_ow_ok"])
        self.assertLess(self.r["routed_token_ratio"], 1.0)

    def test_a_larger_call_budget_removes_most_wins(self):
        t = compare.totals(compare.compare(27, call_cap=40))
        self.assertLessEqual(t["ow_wins"], 1)
        self.assertEqual(compare.CALL_CAP, 24)


class Stick(unittest.TestCase):
    def test_stick_mode_has_no_conflicts(self):
        x = lock.trial("stick")
        self.assertEqual(x.conflicts, 0)
        self.assertGreater(x.overlaps, 1_000)
        self.assertGreater(x.late_refused, 0)

    def test_shared_token_does_not_help(self):
        self.assertEqual(lock.trial("shared").conflicts,
                         lock.trial("none").conflicts)
        self.assertGreater(lock.trial("shared").conflicts, 1_000)

    def test_gateway_checks_the_caller(self):
        s = lock.Stick()
        tok = s.acquire("LTG-5172204", "lead", 0.0)
        s.check("LTG-5172204", "worker", tok, 1.0, by_caller=False)
        with self.assertRaises(StaleLease):
            s.check("LTG-5172204", "worker", tok, 1.0)
        s.check("LTG-5172204", "lead", tok, 1.0)

    def test_a_lapsed_token_is_refused(self):
        s = lock.Stick()
        tok = s.acquire("LTG-5172204", "leg-1", 0.0, ttl=30.0)
        with self.assertRaises(StaleLease):
            s.check("LTG-5172204", "leg-1", tok, 31.0)


class Baton(unittest.TestCase):
    def test_baton_has_no_orphans_and_no_doubles(self):
        x = handoff.trial("baton")
        self.assertEqual((x.orphaned, x.two_owners), (0, 0))
        self.assertGreater(x.unknown, 0)

    def test_the_other_designs_fail_one_way_each(self):
        f = handoff.trial("fire-and-forget")
        a = handoff.trial("ack-and-retry")
        self.assertGreater(f.orphaned, 0)
        self.assertGreater(a.two_owners, 0)


class Hierarchy(unittest.TestCase):
    def test_free_summaries_lose_facts_with_depth(self):
        got = [hierarchy.trial(d, "free").intact for d in (1, 2, 3)]
        self.assertEqual(got, sorted(got, reverse=True))
        self.assertLess(got[2], 0.75 * 1_200)

    def test_pinned_lists_hold(self):
        self.assertGreaterEqual(hierarchy.trial(3, "pinned").intact,
                                1_190)


class Eligibility(unittest.TestCase):
    def test_truth_table(self):
        want = {"E27-07": ("no", "R3"), "E27-08": ("yes", "R3"),
                "E27-10": ("no", "R4"), "E27-11": ("desk", "R5"),
                "E27-14": ("no", "R3"), "E27-15": ("yes", "R2"),
                "E27-17": ("yes", "R3"), "E27-18": ("no", "R3"),
                "E27-20": ("yes", "R4"), "E27-21": ("desk", "R5")}
        got = {t.task_id: truth(t) for t in TASKS}
        for k, v in want.items():
            self.assertEqual(got[k], v, k)
        self.assertEqual(len(TASKS), 24)

    def test_verifier_has_the_claim_gap(self):
        t11 = next(t for t in TASKS if t.task_id == "E27-11")
        self.assertEqual(verify(t11, Answer("yes", "R1")), "")
        self.assertEqual(outcome(t11, Answer("yes", "R1")), "wrong")

    def test_verifier_catches_a_wrong_rule_verdict(self):
        t7 = next(t for t in TASKS if t.task_id == "E27-07")
        self.assertIn("R3 gives no", verify(t7, Answer("yes", "R3")))

    def test_parse(self):
        self.assertEqual(parse('ok {"eligible": "Yes", "rule": "r3"}'),
                         Answer("yes", "R3"))
        self.assertFalse(parse("no json").valid)


class Vote(unittest.TestCase):
    def test_verifier_beats_vote_at_a_third_of_the_tokens(self):
        rows = {x.design: x for x in vote.table()}
        base = rows["single"].tokens
        self.assertGreater(rows["verifier"].success,
                           rows["vote"].success)
        self.assertAlmostEqual(rows["vote"].tokens / base, 3.0, 2)
        self.assertLess(rows["verifier"].tokens / base, 1.2)
        self.assertGreater(rows["debate"].tokens / base, 7.0)

    def test_independent_voters_help_more(self):
        corr = {x.design: x for x in vote.table()}["vote"].success
        ind = {x.design: x for x in vote.table(rho=0.0)}["vote"].success
        self.assertGreater(ind, corr + 0.03)


class Lab(unittest.TestCase):
    def test_card_passes_and_injection_fails(self):
        code, out = _out("--part", "card")
        self.assertEqual(code, 0)
        self.assertIn("* types one agent wins", out)
        code, out = _out("--inject", "shared")
        self.assertEqual(code, 1)
        self.assertIn("CHECK FAILED: conflicting effects", out)

    def test_every_line_fits(self):
        code, out = _out()
        self.assertEqual(code, 0)
        for ln in out.splitlines():
            self.assertLessEqual(len(ln), MAX_LINE, ln)

    def test_card_rows_all_ok(self):
        self.assertTrue(all(r.ok for r in card.rows()))


class LiveReplay(unittest.TestCase):
    def test_fixtures_replay(self):
        cl = live.LowEffortClient("small", SpendMeter(cap_usd=1.0),
                                  FixtureTransport(live.FIXTURES))
        ts = live.run(cl)
        self.assertEqual(ts["single"].calls, 24)
        self.assertEqual(ts["orchestrator"].calls, 96)
        self.assertEqual(ts["debate"].calls, 144)
        for d in live.DESIGNS:
            x = ts[d]
            self.assertEqual(x.correct + x.desk + x.wrong, 24, d)
        self.assertGreater(ts["vote"].tokens, 2.5 * ts["single"].tokens)

    def test_fixtures_hold_no_secrets(self):
        files = list(live.FIXTURES.glob("*.json"))
        self.assertEqual(len(files), 264)
        for p in files:
            self.assertEqual(find_secrets(p.read_text(), fixture=True),
                             [], p.name)


if __name__ == "__main__":
    unittest.main()
