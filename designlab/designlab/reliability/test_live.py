"""Live smoke for Chapter 37: the golden set under the small alias
and the dated snapshot, k=3, under a cent. Skipped unless
ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1. Writes no
fixtures."""
from __future__ import annotations

import unittest

from common.live import skip_unless_live

from . import live


@skip_unless_live
class LiveSmoke(unittest.TestCase):
    def test_echo_matches_pin(self):
        out = live.run(record=False, roles=("small",))
        self.assertTrue(any("echo off pin 0" in ln for ln in out))


if __name__ == "__main__":
    unittest.main()
