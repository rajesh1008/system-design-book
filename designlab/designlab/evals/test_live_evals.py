"""Chapter 34 live test: the small model as a wording judge.

Runs only with ANTHROPIC_API_KEY in the environment (read by the
shared transport, never printed). The replay test runs offline from
the recorded fixtures.
"""
from __future__ import annotations

import unittest

from common.client import FixtureTransport
from common.live import skip_unless_live

from . import live as L


class ReplayTests(unittest.TestCase):
    def test_replay(self):
        out = L.run(FixtureTransport(L.FIXTURES), record=False)
        self.assertIn("30 labeled messages", out[0])
        self.assertIn("UNKNOWN 30", out[4])


@skip_unless_live
class LiveTests(unittest.TestCase):
    def test_live_judge(self):
        out = L.run(record=False)
        kappa = float(out[1].split("kappa ")[1].split()[0])
        self.assertGreaterEqual(kappa, 0.5)
        spent = float(out[-1].split("$")[1].split()[0])
        self.assertLess(spent, L.CAP_USD)


if __name__ == "__main__":
    unittest.main()
