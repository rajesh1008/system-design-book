"""Tests for corpus.ops, the baseline-year operations tables."""
from __future__ import annotations

import unittest

from corpus.ops import OPS_TABLES, generate_ops, ops_digest

# Changing corpus/ops.py changes this digest; the chapter quotes it.
PINNED_OPS_DIGEST = (
    "03a7600046255618c9d359c3ec732cb59e64b46a88191365112ca81f0dbadd21")

T = generate_ops(2026)


class TestOpsCorpus(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(ops_digest(T), ops_digest(generate_ops(2026)))

    def test_pinned(self):
        self.assertEqual(ops_digest(T), PINNED_OPS_DIGEST)

    def test_other_seed_differs(self):
        self.assertNotEqual(ops_digest(generate_ops(7)), ops_digest(T))

    def test_every_table_present(self):
        for name in OPS_TABLES:
            self.assertTrue(T[name], name)

    def test_v0_untouched(self):
        from corpus.generate import TABLES
        self.assertNotIn("ops_changes", TABLES)


if __name__ == "__main__":
    unittest.main()
