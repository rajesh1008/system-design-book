"""Every demo runs offline and prints lines of 70 characters or fewer."""
from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEMOS = ["chain.demo", "common.demo", "corpus.demo", "bank.demo"]


class TestDemos(unittest.TestCase):
    def test_demos_run_and_fit(self):
        env = dict(os.environ, DESIGNLAB_OFFLINE="1")
        env.pop("ANTHROPIC_API_KEY", None)
        for mod in DEMOS:
            with self.subTest(demo=mod):
                r = subprocess.run([sys.executable, "-m", mod], cwd=ROOT,
                                   env=env, capture_output=True,
                                   text=True, timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
                long = [ln for ln in r.stdout.splitlines()
                        if len(ln) > 70]
                self.assertEqual(long, [], f"{mod}: {long[:2]}")
                self.assertTrue(r.stdout.strip())


if __name__ == "__main__":
    unittest.main()
