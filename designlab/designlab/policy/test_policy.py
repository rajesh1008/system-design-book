"""Offline tests for Chapter 31: the policy engine, approval cards,
temporal rules, effect budgets, signed bundles, the kill switch, and
the drills. No network, no model."""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import datetime

from . import demo
from . import drill as D
from .approval import ApprovalGate, Approver
from .bundle import BundleError, BundleStore
from .redteam import battery
from .rules import AUTHOR, BUNDLES, SIGNER
from .tiers import tier_of
from .world import build


def out(fn, *a, **kw) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a, **kw)
    text = buf.getvalue()
    for ln in text.splitlines():
        assert len(ln) <= 70, ln
    return text


class Clock:
    def __init__(self):
        self._t = datetime.fromisoformat("2026-06-22T09:00:00-05:00")

    def now(self):
        return self._t


class Battery(unittest.TestCase):
    def test_nine_of_forty_persuade_the_model(self):
        b = battery()
        self.assertEqual(len(b), 40)
        self.assertEqual(sum(s.persuaded for s in b), 9)

    def test_june_15_bundle_permits_one_the_june_22_none(self):
        t = out(demo.part_talked)
        self.assertIn("permitted 1 of 9", t)
        self.assertIn("permitted 0 of 9", t)
        self.assertIn("payments server requests: 0", t.lower())

    def test_claims_have_no_field_to_reach_the_engine(self):
        self.assertIn("engine input", out(demo.part_talked, claim=True))


class Tiers(unittest.TestCase):
    def test_tiers_follow_the_autonomy_levels(self):
        self.assertEqual(tier_of("refund_ticket", "effect"), "high")
        self.assertEqual(tier_of("rebook_ticket", "effect"), "medium")
        self.assertEqual(tier_of("voucher_issue", "effect"), "low")
        self.assertEqual(tier_of("search_flights", "read"), "read")


class Approval(unittest.TestCase):
    def test_card_rules(self):
        t = out(demo.part_approval)
        for want in ("approver_is_requester", "over_role_limit",
                     "digest_mismatch", "expired"):
            self.assertIn(want, t)

    def test_role_limit(self):
        g = ApprovalGate(Clock())
        c = g.file("refund_ticket", {"amount_usd": "940.00"}, "d1",
                   "agent:servicing", 940.0)
        r = g.decide(c.card_id, Approver("Joanna Reyes", "desk agent",
                                         "person:j.reyes"), "d1", True)
        self.assertEqual(r, "over_role_limit")


class Temporal(unittest.TestCase):
    def test_sequence_rules(self):
        t = out(demo.part_temporal)
        for want in ("repeat_within_window", "quiet_period",
                     "permission_expired"):
            self.assertIn(want, t)


class Budgets(unittest.TestCase):
    def test_day_and_loop_share(self):
        t = out(demo.part_budgets)
        self.assertIn("budget_day", t)
        self.assertIn("budget_loop-share", t)
        self.assertIn("budget_traveler-day", t)
        self.assertIn("$5,000.00", t)


class Bundles(unittest.TestCase):
    def store(self):
        s = BundleStore(Clock())
        s.propose("pb-x", BUNDLES["pb-2026.06.22"], AUTHOR)
        return s

    def test_author_cannot_sign(self):
        with self.assertRaises(BundleError):
            self.store().sign("pb-x", AUTHOR)

    def test_draft_cannot_activate_and_bundles_are_immutable(self):
        s = self.store()
        with self.assertRaises(BundleError):
            s.move("pb-x", "active", SIGNER)
        with self.assertRaises(BundleError):
            s.propose("pb-x", [], AUTHOR)
        s.sign("pb-x", SIGNER)

    def test_shadow_and_which_version(self):
        t = out(demo.part_bundle)
        self.assertIn("66 differ", t)
        self.assertIn("version_revoked", t)
        self.assertIn("refunds-v3", t)


class Coverage(unittest.TestCase):
    def test_every_effect_evaluated(self):
        t = out(demo.part_coverage)
        self.assertIn("100.0%", t)

    def test_engine_down_fails_closed_for_effects(self):
        t = out(demo.part_coverage, engine_down_at=30)
        self.assertIn("forwarded unevaluated: 0", t)
        self.assertIn("effects without a permission                0", t)


class Kill(unittest.TestCase):
    def test_three_tiers(self):
        self.assertIn("tool_held", out(demo.part_kill, tier=1))
        self.assertIn("effects_held", out(demo.part_kill, tier=2))
        self.assertIn("agent_off", out(demo.part_kill, tier=3))

    def test_nothing_late_after_one_poll(self):
        for tier in (1, 2, 3):
            self.assertIn("later than one poll after the pull 0",
                          out(demo.part_kill, tier=tier))

    def test_broken_key_answers_200_and_stops_nothing(self):
        t = out(demo.part_kill, broken=True)
        self.assertIn("switch answered 200", t)
        self.assertIn("safe state observed NO", t)

    def test_drills(self):
        self.assertEqual(D.medians()[3], 70)
        self.assertEqual(D.medians()[1], 40)
        self.assertTrue(all(r.time_to_stop <= 90
                            for t in (1, 2, 3) for r in D.weekly(t)))

    def test_world_builds(self):
        self.assertEqual(build().engine.bundles.active().revision,
                         "pb-2026.06.22")


if __name__ == "__main__":
    unittest.main()
