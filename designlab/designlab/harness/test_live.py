"""Live smoke for Chapter 25: five state-machine runs, one real small
model call each, two cents at most. Skipped unless ANTHROPIC_API_KEY is
set and DESIGNLAB_OFFLINE is not 1. Writes no fixtures."""
from __future__ import annotations

import unittest

from common.live import skip_unless_live

from . import live


@skip_unless_live
class LiveSmoke(unittest.TestCase):
    def test_five_runs_through_the_harness(self):
        out = live.run(record=False)
        body = out[1:-2]
        self.assertEqual(len(body), 5)
        self.assertGreaterEqual(sum(" match " in x for x in body), 4)
        self.assertIn("links intact", out[-2])


if __name__ == "__main__":
    unittest.main()
