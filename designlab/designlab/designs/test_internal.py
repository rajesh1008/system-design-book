"""Tests for Chapter 45's internal designs and rules. Offline.

Every test that needs the twelve designs enters internal.installed(),
which puts Chapter 43's registry, rules, and gap map back on exit.
"""
from __future__ import annotations

import copy
import io
import unittest
from contextlib import redirect_stdout
from importlib import import_module

from common.text import too_long
from designs import demo45, internal, registry
from designs.privilege import prv_1, requested_vs_designed
from designs.recon import lanes, tolerance_trial
from designs.records import due_by_month, rvw_1, to_record
from designs.unattended import loop_1, loop_2, loop_3
from loops.lint import lint as loop_lint
from loops.spec import FARE_WATCH

worked = import_module("designs.lint")
NEW = (loop_1, loop_2, loop_3, prv_1, rvw_1)


def _run(*argv: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = demo45.main(list(argv))
    return rc, buf.getvalue()


def _fault(name: str) -> dict:
    with internal.installed() as designs:
        specs = copy.deepcopy(designs)
        did = demo45._fault(specs, name)
        found = worked.lint(specs[did])
        return {"rules": sorted(f.rule for f in found),
                "gaps": worked.gap_status(specs[did], found)}


class TestInstall(unittest.TestCase):
    def test_twelve_designs_sixty_gaps_no_findings(self):
        with internal.installed() as designs:
            self.assertEqual(len(designs), 12)
            found = {d: worked.lint(s) for d, s in designs.items()}
            self.assertEqual({d: [f.line() for f in x]
                              for d, x in found.items() if x}, {})
            self.assertEqual(sum(worked.gaps_closed(s, found[d])
                                 for d, s in designs.items()), 60)
            self.assertEqual(len(worked.RULES), 13)

    def test_installed_restores_chapter_43(self):
        before = (dict(registry.DESIGNS), list(worked.RULES),
                  dict(worked.GAP_OF))
        with internal.installed():
            pass
        self.assertEqual(tuple(registry.DESIGNS), registry.ORDER)
        self.assertEqual(len(worked.RULES), 8)
        self.assertEqual((dict(registry.DESIGNS), list(worked.RULES),
                          dict(worked.GAP_OF)), before)

    def test_new_rules_silent_on_customer_designs(self):
        for did in registry.ORDER:
            for fn in NEW:
                with self.subTest(design=did, rule=fn.__name__):
                    self.assertEqual(fn(registry.DESIGNS[did]), [])

    def test_specs_are_internal_and_dated(self):
        for did, s in internal.load().items():
            with self.subTest(design=did):
                self.assertEqual(s["design"]["facing"], "internal")
                self.assertEqual(s["design"]["as_of"], "2026-11-02")
        loops = [d for d, s in internal.load().items() if "loop" in s]
        self.assertEqual(len(loops), 5)
        self.assertNotIn("lakeshore-analytics", loops)


class TestFaults(unittest.TestCase):
    def test_no_state_opens_g3_only(self):
        r = _fault("no-state")
        self.assertEqual(r["rules"], ["LOOP-1"])
        self.assertEqual([g for g, ok in r["gaps"].items() if not ok],
                         ["G3"])

    def test_no_change_control(self):
        self.assertEqual(_fault("no-change-control")["rules"],
                         ["HUM-1", "IND-1", "LOOP-2"])

    def test_no_budget(self):
        self.assertEqual(_fault("no-budget")["rules"], ["LOOP-2"])

    def test_raw_sql(self):
        self.assertEqual(_fault("raw-sql")["rules"],
                         ["PRV-1", "PRV-1", "REG-1"])


class TestRules(unittest.TestCase):
    def setUp(self):
        self.specs = internal.load()

    def test_privilege_requested_against_designed(self):
        rows = [requested_vs_designed(s) for s in self.specs.values()]
        self.assertEqual(sum(r["standing_asked"] for r in rows), 14)
        self.assertEqual(sum(r["standing_now"] for r in rows), 0)
        self.assertTrue(all(0 < r["ttl"] <= 60 for r in rows))

    def test_privilege_ttl_and_missing_block(self):
        s = copy.deepcopy(self.specs["lakeshore-coding"])
        s["privilege"]["ttl_minutes"] = 0
        self.assertIn("never expires", prv_1(s)[0].message)
        del s["privilege"]
        self.assertEqual(prv_1(s)[0].message, "no privilege block")

    def test_record_needs_another_signer(self):
        s = copy.deepcopy(self.specs["lakeshore-recon"])
        s["record"]["signer"] = s["record"]["owner"]
        self.assertTrue(any("REC-SIG" in f.message for f in rvw_1(s)))

    def test_record_why_not_from_the_decision(self):
        r = to_record(self.specs["lakeshore-recon"])
        lost = [o for o in r.options if not o.chosen]
        self.assertEqual(len(lost), 2)
        self.assertTrue(all(o.why_not for o in lost))

    def test_december_is_full(self):
        self.assertEqual(due_by_month()["2026-12"], 7)
        s = copy.deepcopy(self.specs["lakeshore-itops"])
        s["record"]["revisit_date"] = "2026-12-14"
        self.assertTrue(any("already holds 7" in f.message
                            for f in rvw_1(s)))
        s["record"]["revisit_date"] = "2026-10-01"
        self.assertTrue(any("not after" in f.message for f in rvw_1(s)))

    def test_loop_verifier_must_be_the_designs(self):
        s = copy.deepcopy(self.specs["lakeshore-recon"])
        s["loop"]["verify"]["verifier"] = "loop:recon-checker"
        self.assertEqual([f.rule for f in loop_3(s)], ["LOOP-3"])

    def test_loop_hand_off_must_be_the_desk(self):
        s = copy.deepcopy(self.specs["lakeshore-coding"])
        s["loop"]["human"]["hand_off"] = "whoever is around"
        self.assertTrue(any("no such desk" in f.message
                            for f in loop_2(s)))

    def test_effect_tools_need_limits(self):
        s = copy.deepcopy(self.specs["lakeshore-itops"])
        del s["loop"]["change"]["effects"]["restart"]
        bad = [f for f in loop_lint(s["loop"]) if not f.ok]
        self.assertEqual([(f.prop, f.why) for f in bad],
                         [("change", "effect restart has no limit")])

    def test_fare_watch_unchanged_by_the_extension(self):
        self.assertTrue(all(f.ok for f in loop_lint(FARE_WATCH)))


class TestRecon(unittest.TestCase):
    def test_widening_buys_matches_with_false_ones(self):
        signed, wide = tolerance_trial()
        self.assertGreater(wide.rate, signed.rate)
        self.assertGreater(wide.false, 10 * max(signed.false, 1))
        self.assertEqual(signed.absorbed_usd, 0.0)

    def test_specialist_lane_decides(self):
        w = lanes()
        self.assertGreater(w["special_hours"], 3 * w["general_hours"])
        self.assertGreater(w["value_left"] / w["value_total"],
                           1 - w["cleared_by_count"])


class TestDemo(unittest.TestCase):
    def test_card(self):
        rc, out = _run("--part", "card")
        self.assertEqual(rc, 0)
        self.assertIn("architectures       12", out)
        self.assertIn("gaps closed         60 of 60", out)
        self.assertIn("worked rules        13", out)

    def test_every_part_fits_seventy_columns(self):
        rc, out = _run()
        self.assertEqual(rc, 0)
        self.assertEqual(too_long(out), [])

    def test_fault_fails(self):
        rc, out = _run("--part", "lint", "--fault", "no-state")
        self.assertEqual(rc, 1)
        self.assertIn("gaps closed 59 of 60, findings 1", out)


if __name__ == "__main__":
    unittest.main()
