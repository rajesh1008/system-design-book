"""Tests for the job-market skill list reader (Chapter 41). Offline."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bank import market


class TestMarket(unittest.TestCase):
    def setUp(self):
        self.ps = market.load()

    def test_rows_and_employers(self):
        self.assertEqual(len(self.ps), 47)
        self.assertEqual(len({p.company for p in self.ps}), 29)
        self.assertEqual([p.row for p in self.ps], list(range(1, 48)))

    def test_no_people_named(self):
        text = market.FIXTURE.read_text(encoding="utf-8")
        for word in ("recruiter", "hiring manager:", "@"):
            self.assertNotIn(word, text)

    def test_tag_is_keyword_based(self):
        self.assertEqual(market.tag("golden sets and guardrails"),
                         frozenset({"evaluation", "control"}))
        self.assertEqual(market.tag("nothing here"), frozenset())

    def test_counts(self):
        c = market.counts(self.ps)
        self.assertEqual(c["control"], 7)
        self.assertEqual(c["evaluation"], 16)
        self.assertEqual(len(market.both(self.ps, "control",
                                         "evaluation")), 3)

    def test_usd_band(self):
        p = next(p for p in self.ps if p.company == "Microsoft")
        self.assertEqual(p.usd_band(), (142.8, 274.8))
        london = next(p for p in self.ps if p.row == 2)
        self.assertIsNone(london.usd_band())

    def test_bad_row(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "m.md"
            f.write_text("| 1 | A | lab | 2026-10 | T |\n")
            with self.assertRaises(ValueError):
                market.load(f)


if __name__ == "__main__":
    unittest.main()
