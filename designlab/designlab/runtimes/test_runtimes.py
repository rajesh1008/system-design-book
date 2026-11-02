"""Tests for the Chapter 30 runtimes lab. Offline; no live calls."""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import unittest

from runtimes import adapters as A
from runtimes import demo
from runtimes import grid as G
from runtimes import portability as P
from runtimes import skills as S


class GridTest(unittest.TestCase):
    def test_loads_and_covers_every_cell(self):
        g = G.load()
        self.assertEqual(len(g.criteria), 22)
        self.assertEqual(len(g.options), 5)
        for o in g.options:
            self.assertEqual(len(o.cells), 22)

    def test_rows_are_the_map_shortlist(self):
        g = G.load()
        self.assertEqual(sorted(o.id for o in g.options),
                         sorted(G.shortlist_ids()))

    def test_ranking(self):
        ids = [o.id for o, _, _ in G.rank(G.load())]
        self.assertEqual(ids[0], "agentcore")
        self.assertEqual(ids[-1], "gemini-agent-runtime")

    def test_portability_weight_keeps_the_leader(self):
        rows = G.rank(G.load(), {"portability": 2})
        self.assertEqual(rows[0][0].id, "agentcore")

    def test_undated_cell_refused(self):
        raw = G.read()
        raw["options"][0]["cells"]["A1"].pop("as_of")
        with self.assertRaisesRegex(G.GridError, "no as_of"):
            G.build(raw)

    def test_cell_after_grid_date_refused(self):
        raw = G.read()
        raw["options"][0]["cells"]["A1"]["as_of"] = "2026-06-24"
        with self.assertRaisesRegex(G.GridError, "after the grid"):
            G.build(raw)

    def test_doc_without_source_refused(self):
        raw = G.read()
        raw["options"][2]["cells"]["C1"]["src"] = "a sales call"
        with self.assertRaisesRegex(G.GridError, "without a source"):
            G.build(raw)

    def test_missing_and_unknown_criteria_refused(self):
        raw = G.read()
        cells = raw["options"][3]["cells"]
        cells["Z9"] = cells.pop("K4")
        with self.assertRaises(G.GridError) as e:
            G.build(raw)
        self.assertIn("Z9: no such criterion", str(e.exception))
        self.assertIn("K4: no cell", str(e.exception))

    def test_bad_score_refused(self):
        raw = G.read()
        raw["options"][0]["cells"]["T1"]["s"] = 3
        with self.assertRaisesRegex(G.GridError, "not 0, 1 or 2"):
            G.build(raw)

    def test_feature_table_refused_everywhere(self):
        with self.assertRaises(G.GridError) as e:
            G.build(G.feature_table(G.read()))
        self.assertEqual(len(str(e.exception).split("; ")), 220)

    def test_extra_option_refused(self):
        raw = G.read()
        extra = dict(raw["options"][0], id="some-new-runtime")
        raw["options"].append(extra)
        with self.assertRaisesRegex(G.GridError, "not the shortlist"):
            G.build(raw)

    def test_stale_on_publication_date(self):
        g = G.load(today=dt.date(2026, 11, 2))
        self.assertEqual(len(g.warnings), 5)
        self.assertTrue(all("22 cells stale" in w for w in g.warnings))
        self.assertEqual(G.load(today=dt.date(2026, 6, 30)).warnings, [])

    def test_must_gate_excludes(self):
        g = G.build(G.drop(G.read(), "agentcore", "T2"))
        last = G.rank(g)[-1]
        self.assertEqual(last[0].id, "agentcore")
        self.assertEqual(last[2], ["T2"])

    def test_drop_memory_ties(self):
        g = G.build(G.drop(G.read(), "agentcore", "K1"))
        totals = {o.id: t for o, t, _ in G.rank(g)}
        self.assertEqual(totals["agentcore"], totals["langgraph"])


class PortabilityTest(unittest.TestCase):
    def test_one_hash_two_adapters(self):
        c = P.check()
        self.assertEqual(set(c.hashes.values()), {"6b225e5fa425"})
        self.assertEqual(c.diffs, [])
        self.assertTrue(c.ok)

    def test_tied_manifest_flagged(self):
        c = P.check(overrides={"loop.resume_from": "thread_id"})
        self.assertFalse(c.ok)
        self.assertIn("thread_id", c.tied[0])

    def test_native_state_does_not_move(self):
        t, s = A.Threads(), A.Sessions()
        t.handle("c1")
        t.save_native("c1", {"at": 1})
        with self.assertRaises(A.NotPortable):
            s.import_native(t.export("c1"))

    def test_session_keys_duplicate_refunds(self):
        m = P.migrate(record="native", key_from="handle")
        self.assertEqual(m.lost, m.moved)
        self.assertGreater(m.duplicates, 0)
        self.assertEqual(m.outcomes["mismatch"], m.duplicates)

    def test_lakeshore_keys_refuse_duplicates(self):
        m = P.migrate(record="native", key_from="run")
        self.assertEqual(m.duplicates, 0)
        self.assertGreater(m.reasked, 0)

    def test_run_store_moves_everything(self):
        m = P.migrate(record="store", key_from="run")
        self.assertEqual((m.lost, m.reasked, m.duplicates), (0, 0, 0))
        base = P.migrate(record="store", key_from="run", killed=0)
        self.assertEqual(m.outcomes, base.outcomes)

    def test_either_direction(self):
        m = P.migrate(record="store", src="sessions", dst="threads")
        self.assertEqual((m.lost, m.duplicates), (0, 0))


class SkillsTest(unittest.TestCase):
    def test_disclosure_costs_less(self):
        led = S.ledger(S.load_all(), {"fare-rules"})
        self.assertLess(led["disclosed"], led["all_upfront"])
        self.assertEqual(led["disclosed"],
                         led["metadata"] + led["loaded"])

    def test_drift_found(self):
        self.assertEqual(S.drift(S.load_all()),
                         ["multi-leg: names fare_quote, not in the "
                          "manifest"])

    def test_skill_front_matter(self):
        for s in S.load_all():
            self.assertTrue(s.name and s.description)


class DemoTest(unittest.TestCase):
    def test_lines_fit(self):
        argv = [["--part", p] for p in sorted(demo.PARTS)]
        argv.append(["--part", "weight", "--weight", "prt=2"])
        argv.append(["--part", "drop", "--drop", "agentcore:K1"])
        for a in argv:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                demo.main(a)
            for line in buf.getvalue().splitlines():
                self.assertLessEqual(len(line), 70, line)


if __name__ == "__main__":
    unittest.main()
