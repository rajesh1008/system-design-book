"""Tests for corpus.fall1, the April 14, 2026 afternoon."""
from __future__ import annotations

import unittest
from collections import Counter, defaultdict

from corpus.fall1 import (DUP_TOTAL_USD, FALL1_TABLES, N_BATCH, N_GATEWAY,
                          fall1_digest, generate_fall1)

# Changing corpus/fall1.py changes this digest; the chapter quotes it.
PINNED_FALL1_DIGEST = (
    "8e1245a11692a210f0fdfb358ee66c0d0843a6540fbad12946bb27123e406484")

T = generate_fall1(2026)


def plans(t):
    out = defaultdict(list)
    for a in t["fall1_attempts"]:
        out[a["refund_id"]].append(a["outcome"])
    return out


class TestFall1Corpus(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(fall1_digest(T), fall1_digest(generate_fall1(2026)))

    def test_pinned(self):
        self.assertEqual(fall1_digest(T), PINNED_FALL1_DIGEST)

    def test_other_seed_differs(self):
        self.assertNotEqual(fall1_digest(generate_fall1(7)), fall1_digest(T))

    def test_every_table_present(self):
        for name in FALL1_TABLES:
            self.assertTrue(T[name], name)

    def test_counts_exact(self):
        paths = Counter(r["path"] for r in T["fall1_refunds"])
        self.assertEqual(paths, {"batch": N_BATCH, "gateway": N_GATEWAY})
        path = {r["refund_id"]: r["path"] for r in T["fall1_refunds"]}
        c = Counter(tuple(v) for k, v in plans(T).items()
                    if path[k] == "batch")
        self.assertEqual(c[("late", "ok")], 194)
        self.assertEqual(c[("late", "late", "ok")], 9)
        self.assertEqual(c[("lost", "ok")], 61)

    def test_duplicate_amounts_sum(self):
        amt = {r["refund_id"]: r["amount_usd"] for r in T["fall1_refunds"]
               if r["path"] == "batch"}
        total = sum(amt[k] * v.count("late") for k, v in plans(T).items()
                    if k in amt)
        self.assertAlmostEqual(total, DUP_TOTAL_USD, places=2)

    def test_ids_unique(self):
        for col in ("refund_id", "itinerary", "permission_id", "charge_id"):
            vals = [r[col] for r in T["fall1_refunds"]]
            self.assertEqual(len(vals), len(set(vals)), col)

    def test_v0_untouched(self):
        from corpus.generate import TABLES
        for name in FALL1_TABLES:
            self.assertNotIn(name, TABLES)


if __name__ == "__main__":
    unittest.main()
