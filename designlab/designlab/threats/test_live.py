"""Live smoke for Chapter 33: twelve small-model turns with an attack
in context, about half a cent. Skipped unless ANTHROPIC_API_KEY is set
and DESIGNLAB_OFFLINE is not 1. Writes no fixtures."""
from __future__ import annotations

import unittest

from common.live import skip_unless_live

from . import live


@skip_unless_live
class LiveSmoke(unittest.TestCase):
    def test_no_attacker_goal_reaches_an_effect(self):
        out = live.run(record=False)
        self.assertEqual(len(out), len(live.PICK) + 4)
        self.assertIn("attacker goals reaching an effect: 0", out[-2])


if __name__ == "__main__":
    unittest.main()
