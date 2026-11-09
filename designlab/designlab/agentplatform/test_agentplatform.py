"""Offline tests for Chapter 40: the template, the extraction, the
golden path, the six conformance tests, evidence-chain coverage,
platform economics, the onboarding logs, and the platform card."""
from __future__ import annotations

import contextlib
import io
import unittest

from gateway.core import Caller
from gateway.servers import loyalty_server
from policy.engine import Request
from policy.world import build as build_june

from . import (card, chain, conformance, demo, economics, onboard,
               onboarding, plane, template)


def fresh(bypass: int = 0, loyalty: dict | None = None):
    p = plane.build()
    obs = onboard.extract(p)
    obs.append(onboard.onboard(p, loyalty or template.load("loyalty"),
                               "pb-2026.08.24", bypass=bypass))
    return p, obs


class Template(unittest.TestCase):
    def test_three_manifests_are_clean(self):
        p = plane.build()
        rules = p.world.bundles.active().rules
        for name in template.USE_CASES:
            m = onboard.with_kinds(p, template.load(name))
            self.assertEqual(template.check(m, rules), [], name)

    def test_as_built_has_twelve_problems(self):
        probs = template.check(template.as_built_aug10())
        self.assertEqual(len(probs), 12)
        self.assertIn("platform-owned: gateway (the shared gateway)",
                      probs)
        self.assertTrue(any("needs 30" in x for x in probs))

    def test_platform_owned_key_refused(self):
        m = template.load("loyalty")
        m["use_case"]["policy_engine"] = "ours"
        self.assertIn("platform-owned: policy_engine (the policy "
                      "engine)", template.check(m))

    def test_new_effect_needs_a_limit(self):
        m = template.load("loyalty")
        m["policy"]["rules"] = [r for r in m["policy"]["rules"]
                                if r["type"] != "limit"]
        self.assertIn("effect points_credit has no limit",
                      template.check(m))

    def test_verifier_cannot_be_the_owner(self):
        m = template.load("loyalty")
        m["verify"]["owner"] = m["use_case"]["owner"]
        self.assertIn("verifier owner is the use case owner",
                      template.check(m))


class Project(unittest.TestCase):
    def test_loyalty_cannot_use_the_project_plane(self):
        w = build_june(start="2026-08-10T14:00:00-05:00")
        w.servers["loyalty-points"] = loyalty_server()
        r = w.gateway.call("wl-loyalty-agent", "loyalty-points",
                           "points_credit", {"points": 2500})
        self.assertEqual(r.reason, "unauthenticated")
        r = w.gateway.call("wl-servicing-agent", "loyalty-points",
                           "points_balance", {"customer_id": "C-1"})
        self.assertEqual(r.reason, "not_registered")
        d = w.engine.decide(Request("agent:loyalty", "points_credit",
                                    "effect", {"points": 2500}, "s"))
        self.assertEqual((d.verdict, d.reason), ("deny", "no_rule"))


class Extraction(unittest.TestCase):
    def test_both_live_and_hard_wiring_gone(self):
        p = plane.build()
        self.assertEqual(sorted(p.gateway.callers), ["wl-fare-watch"])
        obs = onboard.extract(p)
        self.assertTrue(all(o.live for o in obs))
        self.assertEqual(sorted(p.gateway.callers),
                         ["wl-desk-assistant", "wl-fare-watch",
                          "wl-servicing-agent"])
        self.assertEqual(len(p.gateway.callers["wl-desk-assistant"]
                             .tools), 6)


class GoldenPath(unittest.TestCase):
    def test_loyalty_goes_live(self):
        p, obs = fresh()
        ob = obs[-1]
        self.assertTrue(ob.live)
        self.assertEqual([s for s, _, _ in ob.steps],
                         ["template", "identity", "registry", "review",
                          "staging", "conformance"])
        b = p.world.bundles.active()
        self.assertEqual((b.revision, len(b.rules)),
                         ("pb-2026.08.24", 18))

    def test_registry_finding_stops_it(self):
        m = template.load("loyalty")
        m["tools"][0]["description"] = ("Get the member's points "
                                        "balance and update their tier.")
        p, obs = fresh(loyalty=m)
        ob = obs[-1]
        self.assertFalse(ob.live)
        self.assertEqual(ob.steps[-1][0], "registry")
        self.assertIn("writes", ob.steps[-1][2])
        self.assertNotIn("loyalty-points",
                         {e.server for e in p.registry.approved()})


class Conformance(unittest.TestCase):
    def test_six_of_six(self):
        p, obs = fresh()
        for o in obs:
            self.assertEqual(conformance.passed(o.checks), 6, o.use_case)

    def test_bypass_fails_k2_only(self):
        p, obs = fresh(bypass=1)
        bad = [c for c in obs[-1].checks if not c.ok]
        self.assertEqual([c.id for c in bad], ["K2"])
        self.assertEqual(bad[0].detail,
                         "loyalty-points: 1 request not forwarded")
        self.assertFalse(obs[-1].live)

    def test_wider_grant_fails_k1(self):
        p, obs = fresh()
        m = p.manifests["loyalty"]
        c = p.gateway.callers["wl-loyalty-agent"]
        p.gateway.callers["wl-loyalty-agent"] = Caller(
            c.sub, c.tools | {"refund_ticket"})
        self.assertFalse(conformance.k1_identity(p, m, p.lines()).ok)

    def test_limit_boundary(self):
        p, _ = fresh()
        m = p.manifests["loyalty"]
        t = plane.Tracer("t")
        for pts, ok, why in ((5000, True, ""),
                             (5001, False, "routed_to_person")):
            p.clock.advance(30)
            args = {"member_id": "MBR-30000777", "points": pts,
                    "reason": "service"}
            r = p.call(m, p.mint(m, "MBR-30000777"), "loyalty-points",
                       "points_credit", args, t)
            self.assertEqual((r.ok, r.reason), (ok, why), pts)

    def test_missing_spans_fail_k6(self):
        p, _ = fresh()
        p.run("loyalty", skip_spans=True)
        c = conformance.k6_trace(p, p.manifests["loyalty"], p.lines())
        self.assertFalse(c.ok)
        self.assertIn("no span", c.detail)


class Chain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.obs = card.august()

    def test_two_of_three(self):
        cov = {n: chain.use_case_covered(self.p, self.p.manifests[n])
               for n in template.USE_CASES}
        self.assertEqual(cov, {"servicing": True, "desk": True,
                               "loyalty": False})

    def test_loyalty_misses_only_verify(self):
        full, n, miss = chain.coverage(self.p, self.p.manifests["loyalty"])
        self.assertEqual((full, miss), (0, ["verify"]))
        self.assertEqual(n, 25)

    def test_decision_digest_matches_call(self):
        lines = self.p.lines()
        for e in chain.calls_of(lines, "agent:loyalty"):
            if e["tool"] == "points_credit" and e["verdict"] == "allowed":
                d = chain.decision_for(lines, e)
                self.assertEqual(d["digest"], e["args_digest"])

    def test_coverage_cannot_see_a_bypass(self):
        a, _ = fresh()
        b, _ = fresh(bypass=1)
        ca = chain.coverage(a, a.manifests["loyalty"])
        cb = chain.coverage(b, b.manifests["loyalty"])
        self.assertEqual(ca, cb)


class Economics(unittest.TestCase):
    def test_break_even(self):
        self.assertAlmostEqual(economics.break_even(), 2.68, 2)
        self.assertEqual((economics.duplicated(3), economics.shared(3)),
                         (67_500, 61_000))
        self.assertEqual((economics.duplicated(10),
                          economics.shared(10)), (225_000, 75_000))

    def test_charging_by_calls_drives_out_the_largest(self):
        rows = {r[0]: r for r in economics.charges()}
        self.assertGreater(rows["servicing"][1], rows["servicing"][4])
        self.assertLess(rows["loyalty"][4] - rows["loyalty"][2], 2_200)
        self.assertTrue(all(r[3] < r[4] for r in rows.values()))


class Logs(unittest.TestCase):
    def test_thirty_one_and_nine(self):
        self.assertEqual(onboarding.total(onboarding.DESK), 31)
        self.assertEqual(sum(s.days for s in onboarding.DESK), 31)
        self.assertEqual(onboarding.meetings(onboarding.DESK), 11)
        self.assertEqual(onboarding.total(onboarding.LOYALTY), 9)
        self.assertEqual(onboarding.meetings(onboarding.LOYALTY), 1)


class Card(unittest.TestCase):
    def test_card(self):
        p, obs = card.august()
        c = card.compute(p, obs)
        self.assertEqual(c["use_cases"], 3)
        self.assertEqual(c["covered"], ["servicing", "desk"])
        self.assertEqual(set(c["conformance"].values()), {6})
        self.assertEqual((c["onboard_days"], c["before_days"]), (9, 31))

    def test_trail_chain_intact(self):
        from common.trail import check_trail
        p, _ = card.august()
        self.assertEqual(check_trail(p.trail.lines), [])


class Demo(unittest.TestCase):
    def test_every_part_fits_70(self):
        for extra in ([], ["--as-built"], ["--bypass"], ["--charge"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                demo.main(extra)
            self.assertTrue(buf.getvalue())


if __name__ == "__main__":
    unittest.main()
