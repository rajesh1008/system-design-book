"""Offline tests for the Chapter 21 lab. No key, no network."""
from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout

from common.clock import FixedClock
from common.client import FixtureTransport
from common.redact import find_secrets
from common.spend import SpendMeter
from common.trail import TrailWriter, check_trail

from . import compact, demo, drift, isolate, live, rot, transcript
from .assemble import assemble, reuse
from .runs import make_runs, opening_run
from .slots import BUDGET, Budget, Item, stable_items


def parts(**extra):
    p = {"tools": [], "instructions": [], "policy": [], "examples": []}
    for it in stable_items():
        p[it.slot].append(it)
    p.update(extra)
    return p


class Budgets(unittest.TestCase):
    def test_knee_and_budget_come_from_the_harness(self):
        k = rot.knee(rot.harness(21))
        self.assertEqual(k, 60_000)
        self.assertEqual(rot.budget_from(k), 48_000)
        self.assertEqual(Budget(BUDGET).trigger, 33_600)

    def test_rot_curve_is_flat_then_falls(self):
        self.assertLess(abs(rot.success_at(10_000)
                            - rot.success_at(50_000)), 0.01)
        self.assertLess(rot.success_at(120_000), 0.90)


class Assembler(unittest.TestCase):
    def test_stable_first_lints_clean_and_retrieved_first_does_not(self):
        p = parts(retrieved=[Item("retrieved", "d1", 300, 1)])
        self.assertEqual(assemble(p).findings, [])
        order = ("retrieved", "tools", "instructions", "policy",
                 "examples")
        found = assemble(p, order=order).findings
        self.assertEqual(len(found), 1)
        self.assertIn("ahead of 2,840 stable tokens", found[0])

    def test_cap_cuts_lowest_rank_and_raises_an_alarm(self):
        docs = [Item("retrieved", f"d{i}", 900, i) for i in range(4)]
        a = assemble(parts(retrieved=docs))
        self.assertEqual(a.by_slot["retrieved"], 1_800)
        self.assertEqual([i.key for i in a.items
                          if i.slot == "retrieved"], ["d0", "d1"])
        self.assertEqual(a.alarms, ["cap retrieved cut 1,800"])

    def test_stable_slot_over_cap_alarms_but_is_not_cut(self):
        p = parts()
        p["instructions"] = stable_items(release="v8")[1:2]
        a = assemble(p)
        self.assertEqual(a.by_slot["instructions"], 1_460)
        self.assertEqual(a.alarms, ["cap instructions 1,460 > 1,200"])
        p["instructions"] = stable_items(release="v9")[1:2]
        self.assertEqual(assemble(p).alarms, [])

    def test_budget_breach_writes_a_chicago_trail_line(self):
        trail = TrailWriter(clock=FixedClock(demo.CHICAGO_MAY12, 0.5))
        hist = [Item("history", "h1", 50_000, 0)]
        a = assemble(parts(history=hist), trail=trail, run="R-1", step=9)
        self.assertTrue(a.over_budget)
        line = json.loads(trail.lines[0])
        self.assertEqual(line["event"], "context.alarm")
        self.assertEqual(line["alarm"],
                         "budget 52,840 > 48,000 (history 50,000)")
        self.assertEqual(demo.alarm_slot(line["alarm"]), "history")
        self.assertTrue(line["at"].endswith("-05:00"))
        self.assertEqual(check_trail(trail.lines), [])

    def test_prefix_reuse_stops_at_the_clock(self):
        p = parts(clock=[Item("clock", "t1", 12, 0)],
                  history=[Item("history", "h1", 500, 0)])
        a = assemble(p)
        p2 = dict(p, clock=[Item("clock", "t2", 12, 0)])
        self.assertEqual(reuse(a, assemble(p2)), 2_840 + 500)


class Opening(unittest.TestCase):
    def test_opening_run_peaks_at_110412(self):
        run = opening_run()
        res = compact.replay(run, "none", alarms_on=False)
        self.assertEqual(run.run_id, "R-0423-0117")
        self.assertEqual(run.length, 22)
        self.assertEqual(res.peak, 110_412)
        self.assertIn("two children", run.steps[1].facts[0].text)


class Compaction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = make_runs(21)
        cls.res = {p: [compact.replay(r, p, Budget(), 21)
                       for r in cls.runs] for p in compact.POLICIES}

    def lost(self, p):
        return sum(bool(x.lost) for x in self.res[p])

    def test_pinned_loses_nothing_and_files_no_second_card(self):
        self.assertEqual(self.lost("pinned"), 0)
        self.assertEqual(sum(x.second_card for x in self.res["pinned"]), 0)

    def test_free_summary_loses_facts_and_truncation_loses_more(self):
        self.assertEqual(self.lost("summary"), 54)
        self.assertEqual(sum(x.second_card for x in self.res["summary"]),
                         26)
        self.assertGreater(self.lost("truncate"), self.lost("summary"))

    def test_none_never_compacts(self):
        self.assertEqual(sum(x.compactions for x in self.res["none"]), 0)


class Verifier(unittest.TestCase):
    def test_free_summary_fails_and_structured_passes(self):
        got = compact.verify_summary(demo.SUMMARY_FREE, demo.PINNED,
                                     demo.TRAIL)
        self.assertIn("dropped APR-48213", got)
        self.assertIn("dropped idem-LTG-5318806-rf1", got)
        self.assertEqual(compact.verify_summary(
            demo.SUMMARY_PINNED, demo.PINNED, demo.TRAIL), [])

    def test_one_changed_digit_is_caught_twice(self):
        bad = demo.SUMMARY_PINNED.replace("$412.80", "$421.80")
        self.assertEqual(compact.verify_summary(bad, demo.PINNED,
                                                demo.TRAIL),
                         ["dropped $412.80", "not in trail $421.80"])


class Isolation(unittest.TestCase):
    def test_sub_agent_cannot_hold_or_use_an_effect_tool(self):
        with self.assertRaises(isolate.NotPermitted):
            isolate.SubAgent("bad", frozenset({"refund.issue"}))
        w = isolate.SubAgent("fare-rule-research")
        with self.assertRaises(isolate.NotPermitted):
            w.use("refund.issue")
        self.assertEqual(w.calls, [])

    def test_artifact_store_reads_a_slice_by_handle(self):
        s = isolate.ArtifactStore()
        h = s.put("R-1", 4, "\n".join(f"row {i}" for i in range(20)))
        self.assertEqual(h, "art://R-1/s4")
        self.assertEqual(s.read(h, 2, 2), "row 2\nrow 3")

    def test_isolation_sends_less_to_the_lead(self):
        runs = make_runs(21)[:300]
        a = sum(compact.replay(r, "pinned").sent for r in runs)
        b = sum(compact.replay(isolate.isolate(r).run, "pinned").sent
                for r in runs)
        self.assertLess(b, a)


class Drift(unittest.TestCase):
    def test_versions_match_the_table(self):
        h = {v: (n, t, f) for v, _, n, t, f in drift.history()}
        self.assertEqual(h["v7"][:2], (56, 1_100))
        self.assertEqual(h["v8"][:2], (71, 1_460))
        self.assertEqual(len(h["v8"][2]["stale"]), 9)
        self.assertEqual(len(h["v8"][2]["contradiction"]), 3)
        n, t, f = h["v9"]
        self.assertEqual((n, t), (58, 1_180))
        for k in ("stale", "contradiction", "no owner"):
            self.assertEqual(f[k], [])

    def test_quoted_lines(self):
        q = drift.lint(list(drift.QUOTED))
        self.assertEqual(q["stale"], ["L-019", "L-033"])
        self.assertEqual(q["no owner"], ["L-007", "L-019"])


class Card(unittest.TestCase):
    def run_demo(self, *args):
        out = io.StringIO()
        with redirect_stdout(out):
            code = demo.main(list(args))
        return code, out.getvalue()

    def test_production_card_passes(self):
        code, out = self.run_demo("--part", "card")
        self.assertEqual(code, 0)
        self.assertIn("98.3% (was 90.7%)", out)
        self.assertIn("check passed", out)

    def test_shadow_week_alarms_by_slot(self):
        code, out = self.run_demo("--part", "alarms")
        self.assertIn("instructions   17,385 (100.0%)", out)
        self.assertIn("history         2,580 (14.8%)", out)
        self.assertIn("first at 2026-05-05T08:00:00-05:00", out)

    def test_injected_unnoticed_breach_fails_the_check(self):
        code, out = self.run_demo("--inject", "unnoticed")
        self.assertEqual(code, 1)
        self.assertIn("CHECK FAILED: steps over budget, unnoticed", out)

    def test_demo_lines_fit_70_columns(self):
        for args in (("--part", "assemble", "--retrieved-first"),
                     ("--part", "drift"), ("--part", "verify"),
                     ("--part", "alarms"),
                     ("--part", "opening")):
            _, out = self.run_demo(*args)
            for line in out.splitlines():
                self.assertLessEqual(len(line), 70, line)


class LiveFixtures(unittest.TestCase):
    """The recorded live calls replay offline through the same code."""

    def test_long_context_sample_replays(self):
        cl = live.LowEffortClient("small", SpendMeter(cap_usd=1.0),
                                  FixtureTransport(live.FIXTURES))
        rows = live.run(cl)
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r["input_tokens"] < 90_000 for r in rows))
        self.assertEqual(sum(r["ok"] for r in rows), 6)

    def test_compaction_prompts_replay(self):
        from models import compaction
        cl = live.LowEffortClient("small", SpendMeter(cap_usd=1.0),
                                  FixtureTransport(compaction.FIXTURES))
        rows = compaction.run(cl)
        free = [r for r in rows if r["prompt"] == "free"]
        struct = [r for r in rows if r["prompt"] == "structured"]
        self.assertTrue(all(r["findings"] for r in free))
        self.assertTrue(all(not r["findings"] for r in struct))

    def test_fixtures_hold_no_secrets(self):
        from models import compaction
        for d in (live.FIXTURES, compaction.FIXTURES):
            for p in d.glob("*.json"):
                self.assertEqual(find_secrets(p.read_text(),
                                              fixture=True), [], p.name)

    def test_transcripts_are_seeded(self):
        f = transcript.facts(21, 0)
        self.assertEqual(transcript.transcript(f, 21, 0, 4_000),
                         transcript.transcript(f, 21, 0, 4_000))


if __name__ == "__main__":
    unittest.main()
