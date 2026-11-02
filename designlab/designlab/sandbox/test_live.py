"""Live smoke for Chapter 29: six small-model calls as the coding agent
on FR-207, under a cent. Skipped unless ANTHROPIC_API_KEY is set and
DESIGNLAB_OFFLINE is not 1. Writes no fixtures."""
from __future__ import annotations

import unittest

from common.live import skip_unless_live

from . import live


@skip_unless_live
class LiveSmoke(unittest.TestCase):
    def test_every_proposal_waits_for_a_person(self):
        out = live.run(record=False)
        gates = [ln for ln in out if "gate" in ln]
        self.assertEqual(len(gates), 6)
        self.assertFalse(any("merge:" in g for g in gates))


if __name__ == "__main__":
    unittest.main()
