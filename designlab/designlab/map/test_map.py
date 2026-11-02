"""Offline tests for the map: parser, validator, shortlist, demo."""
from __future__ import annotations

import copy
import datetime as dt
import io
import unittest
from contextlib import redirect_stdout

from . import demo
from .model import GAP_IDS, MAP_FILE, build, load
from .shortlist import rank, recheck, score, shortlist
from .yamlish import YamlishError, loads

RAW = loads(MAP_FILE.read_text())


def with_row(**changes):
    raw = copy.deepcopy(RAW)
    row = copy.deepcopy(demo.INJECTED)
    row["claims"][0]["as_of"] = "2026-10-01"
    row.update(changes)
    raw["options"].append(row)
    return build(raw)


class TestYamlish(unittest.TestCase):
    def test_nested_lists_and_flow_maps(self):
        d = loads("a:\n  - x: 1\n    g: {G1: closes}\n    l: [p, q]\n")
        self.assertEqual(d, {"a": [{"x": 1, "g": {"G1": "closes"},
                                    "l": ["p", "q"]}]})

    def test_dates_stay_strings_and_comments_drop(self):
        d = loads('d: 2026-11-02  # comment\nu: "a # b"\n')
        self.assertEqual(d, {"d": "2026-11-02", "u": "a # b"})

    def test_duplicate_key_and_tab_refused(self):
        with self.assertRaises(YamlishError):
            loads("a: 1\na: 2\n")
        with self.assertRaises(YamlishError):
            loads("a:\n\t- 1\n")


class TestMap(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def test_counts(self):
        self.assertTrue(self.m.ok, self.m.errors)
        self.assertEqual(len(self.m.categories), 7)
        self.assertEqual(len(self.m.options), 31)
        counts = {c: len(v) for c, v in self.m.by_category().items()}
        self.assertEqual(counts, {"framework": 7, "runtime": 5,
                                  "protocol": 5, "gateway": 4,
                                  "policy": 2, "inference": 4,
                                  "evaluation": 4})

    def test_every_claim_dated_and_sourced(self):
        for o in self.m.options:
            for c in o.claims:
                self.assertLessEqual(c.as_of, self.m.as_of, o.id)
                self.assertTrue(c.source.startswith("https://"), o.id)

    def test_nothing_closes_g4_or_g5(self):
        for o in self.m.options:
            for g in ("G4", "G5"):
                self.assertNotEqual(o.gaps[g], "closes", o.id)

    def test_struck_row(self):
        self.assertEqual([s["id"] for s in self.m.struck],
                         ["openai-agent-builder"])


class TestValidator(unittest.TestCase):
    def test_undated_claim_refused(self):
        raw = copy.deepcopy(RAW)
        raw["options"].append(copy.deepcopy(demo.INJECTED))
        m = build(raw)
        self.assertFalse(m.ok)
        self.assertIn("acme-agent-cloud claim 1: no as_of date", m.errors)
        self.assertEqual(len(m.options), 31)

    def test_bad_rows_refused(self):
        cases = {
            "category": ("platform", "unknown category"),
            "lock_in": (9, "lock_in must be 1 to 5"),
            "status": ("forever", "unknown status"),
        }
        for key, (value, msg) in cases.items():
            m = with_row(**{key: value})
            self.assertTrue(any(msg in e for e in m.errors), key)

    def test_unknown_gap_code_and_source(self):
        gaps = dict(demo.INJECTED["gaps"], G2="mostly")
        self.assertFalse(with_row(gaps=gaps).ok)
        claims = [{"text": "x", "gap": "G2", "as_of": "2026-10-01",
                   "source": "http://example.com"}]
        m = with_row(claims=claims)
        self.assertIn("acme-agent-cloud claim 1: no https source",
                      m.errors)

    def test_future_claim_refused(self):
        claims = [{"text": "x", "gap": "G2", "as_of": "2027-01-01",
                   "source": "https://example.com"}]
        self.assertFalse(with_row(claims=claims).ok)

    def test_duplicate_id_refused(self):
        self.assertFalse(with_row(id="langgraph").ok)

    def test_well_formed_row_loads(self):
        m = with_row()
        self.assertTrue(m.ok, m.errors)
        self.assertEqual(len(m.options), 32)


class TestShortlist(unittest.TestCase):
    def setUp(self):
        self.m = load()

    def names(self, picks, cat):
        return [s.option.id for s in picks[cat]]

    def test_shortlist(self):
        p = shortlist(self.m)
        self.assertEqual(self.names(p, "runtime"),
                         ["langsmith-deployment", "agentcore",
                          "gemini-agent-runtime"])
        self.assertEqual(self.names(p, "framework"),
                         ["langgraph", "ms-agent-framework"])

    def test_exclusions_have_reasons(self):
        r = {s.option.id: s.reason for s in rank(self.m, "framework")}
        self.assertEqual(r["openai-agents-sdk"], "status pre-1.0")
        self.assertEqual(r["crewai"], "")
        rt = {s.option.id: s.reason for s in rank(self.m, "runtime")}
        self.assertEqual(rt["claude-managed-agents"], "status beta")

    def test_score(self):
        ac = next(o for o in self.m.options if o.id == "agentcore")
        self.assertEqual(ac.points, 4)
        self.assertEqual(score(ac), 2.5)
        self.assertEqual(score(ac, 2.0), 1.0)

    def test_lockin_twice_keeps_shortlist(self):
        one, two = shortlist(self.m), shortlist(self.m, 2.0)
        for cat in ("runtime", "framework"):
            self.assertEqual(self.names(one, cat), self.names(two, cat))

    def test_aging_six_months_flags_shortlist(self):
        old = load(today=dt.date(2027, 5, 2))
        self.assertEqual(len(recheck(old, shortlist(old))), 5)
        self.assertEqual(recheck(self.m, shortlist(self.m)), [])


class TestDemo(unittest.TestCase):
    def test_demo_lines_and_exit(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = demo.main([])
        out = buf.getvalue().splitlines()
        self.assertEqual(rc, 0)
        self.assertTrue(all(len(x) <= 70 for x in out))
        self.assertIn("   refused: acme-agent-cloud claim 1: no as_of date",
                      out)
        self.assertEqual(GAP_IDS, ("G1", "G2", "G3", "G4", "G5"))


if __name__ == "__main__":
    unittest.main()
