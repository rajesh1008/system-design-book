"""Offline tests for Chapter 25: the manifest, the deploy check, the
trail, the two loop shapes and the harness suite itself.

HARNESS_INJECT=settings applies the May 27 settings-file edit before
the deploy test; that test is then expected to fail.
"""
from __future__ import annotations

import json
import os
import unittest

from common.client import FixtureTransport
from common.trail import check_trail

from . import deploy, live, loops, suite
from . import manifest as M
from .tools import PASTED, catalog
from .world import cases

V1 = "servicing-1.0.0"
V11 = "servicing-1.1.0"
RC1 = "servicing-1.0.0-rc1"


def resolved(name):
    return M.resolve(M.load(name))


class TestManifest(unittest.TestCase):
    def test_v1_declares_fourteen_tools_and_four_stops(self):
        c = M.counts(resolved(V1))
        self.assertEqual((c["tools"], c["stops"]), (14, 4))
        self.assertNotIn("hotel_cancel",
                         [t["name"] for t in resolved(V1)["tools"]])

    def test_every_section_present_or_refused(self):
        raw = M.load(V1)
        del raw["context"]
        with self.assertRaises(M.ManifestError):
            M.resolve(raw)

    def test_tool_version_must_match_catalog(self):
        raw = M.load(V1)
        raw["tools"][9]["version"] = "2.0"
        with self.assertRaises(M.ManifestError):
            M.resolve(raw)

    def test_hash_is_stable_and_order_free(self):
        a = resolved(V1)
        b = json.loads(json.dumps(a, sort_keys=False))
        self.assertEqual(M.manifest_hash(a), M.manifest_hash(b))

    def test_description_moves_hash_not_tool_version(self):
        old = catalog()
        d = old["rebook_ticket"]["description"]
        old["rebook_ticket"] = dict(old["rebook_ticket"],
                                    description=d.replace(" " + PASTED, ""))
        before = M.resolve(M.load(V1), tools=old)
        after = resolved(V1)
        self.assertEqual(before["tools"][8]["version"],
                         after["tools"][8]["version"])
        self.assertEqual(M.diff(before, after),
                         ["tools[rebook_ticket].description"])


class TestDeploy(unittest.TestCase):
    def test_registered_release_deploys(self):
        ov = ({"context.keep_turns": 3}
              if os.environ.get("HARNESS_INJECT") == "settings" else {})
        v = deploy.check(M.load(V1), ov)
        self.assertTrue(v.ok, v.reason)

    def test_registry_matches_every_manifest_on_disk(self):
        reg = deploy.releases()
        for name in (V1, V11):
            h = resolved(name)
            self.assertEqual(reg[h["version"]]["hash"],
                             M.manifest_hash(h), name)

    def test_settings_override_is_refused(self):
        v = deploy.check(M.load(V1), {"context.keep_turns": 3})
        self.assertFalse(v.ok)
        self.assertIn("hash", v.reason)

    def test_unregistered_candidate_and_blank_refused(self):
        self.assertFalse(deploy.check(M.load(RC1)).ok)
        self.assertFalse(deploy.check(M.load(V11)).ok)
        self.assertFalse(deploy.check(M.load(V1), {"version": ""}).ok)


class TestTrail(unittest.TestCase):
    def test_every_line_carries_version_and_hash(self):
        for name, shape in ((V1, "react"), (V11, "sm")):
            h = resolved(name)
            hz = loops.Harness(h, trail=loops.new_trail())
            for c in cases(25):
                (loops.react(c, hz) if shape == "react"
                 else loops.state_machine(c, hz))
            lines = [json.loads(x) for x in hz.trail.lines]
            self.assertTrue(lines)
            self.assertTrue(all(e["manifest"] == hz.hash and
                                e["harness"] == h["version"]
                                for e in lines))
            self.assertEqual(check_trail(hz.trail.lines), [])

    def test_may28_edit_is_visible_only_in_the_hash(self):
        base = resolved(V1)
        may27 = M.apply_overrides(base, {"version": "2026.05.26-1"})
        may28 = M.apply_overrides(may27, {"context.keep_turns": 3})
        self.assertEqual(may27["version"], may28["version"])
        self.assertNotEqual(M.manifest_hash(may27), M.manifest_hash(may28))
        self.assertEqual(M.diff(may27, may28), ["context.keep_turns"])


class TestShapes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h = resolved(V11)
        hz = loops.Harness(cls.h)
        cs = cases(1000)
        cls.react = [loops.react(c, hz) for c in cs]
        cls.sm = [loops.state_machine(c, hz) for c in cs]

    def test_state_machine_has_no_illegal_transitions(self):
        self.assertEqual(sum(r.illegal for r in self.sm), 0)
        self.assertEqual({r.steps for r in self.sm}, {5, 7})

    def test_react_varies_and_is_refused_sometimes(self):
        steps = [r.steps for r in self.react]
        self.assertGreater(max(steps) - min(steps), 10)
        self.assertGreater(sum(r.illegal for r in self.react), 0)

    def test_react_never_completes_an_unverified_effect(self):
        for r in self.react:
            if r.outcome == "done":
                self.assertEqual(r.stop, "verified")

    def test_amount_only_from_fare_calc(self):
        hz = loops.Harness(self.h)
        for c in cases(100):
            w = loops.World()
            loops.state_machine(c, hz, world=w)
            self.assertIn(w.reconcile(c), (c.fare_left, 0))


class TestSuite(unittest.TestCase):
    def test_v1_and_v11_pass_every_check(self):
        for name in (V1, V11):
            bad = [r for r in suite.run(resolved(name)) if r[2]]
            self.assertEqual(bad, [], name)

    def test_first_build_fails_four_named_checks(self):
        bad = sorted(fn for _, fn, why in suite.run(resolved(RC1)) if why)
        self.assertEqual(bad, ["budget_matches_enforcer",
                               "context_ref_survives",
                               "stop_no_progress",
                               "tool_timeout_retried"])

    def test_every_forbidden_transition_refused(self):
        self.assertIsNone(suite.transitions_forbidden(resolved(V11)))


class TestLiveReplay(unittest.TestCase):
    def test_recorded_smoke_runs_replay_offline(self):
        out = live.run(FixtureTransport(live.FIXTURES), record=False)
        body = out[1:-2]
        self.assertEqual(len(body), 5)
        self.assertTrue(all(" match " in x for x in body), body)
        self.assertIn("with manifest hash 34", out[-2])


if __name__ == "__main__":
    unittest.main()
