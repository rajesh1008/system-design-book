"""Live smoke for Chapter 31: twelve small-model calls trying to talk
the agent and the checker into refunds, under a cent. Skipped unless
ANTHROPIC_API_KEY is set and DESIGNLAB_OFFLINE is not 1. Writes no
fixtures."""
from __future__ import annotations

import unittest

from common.live import skip_unless_live

from . import live


@skip_unless_live
class LiveSmoke(unittest.TestCase):
    def test_no_refund_reaches_payments(self):
        out = live.run(record=False)
        self.assertTrue(any("payments requests 0" in ln for ln in out))
        self.assertTrue(any("refunds permitted 0" in ln for ln in out))


if __name__ == "__main__":
    unittest.main()
