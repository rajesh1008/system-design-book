"""Live: twenty argument cases against the small model (about 60 calls)."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveToolArgs(unittest.TestCase):
    def test_shape_holds_and_world_catches(self):
        from toolargs.live import run, summarize
        results = run()
        cases = [r for r in results if "name" in r]
        meta = results[-1]
        self.assertEqual(len(cases), 20)
        # Strict tool use: every proposal is well formed unless the
        # response was cut off at max_tokens, which the docs list as a
        # case the guarantee does not cover. The intake catches it.
        for r in cases:
            for a in r["attempts"]:
                if not a["shape"]:
                    self.assertEqual(a["stop"], "max_tokens", r["name"])
                    self.assertFalse(a["ok"])
        # The clean cases pass; nothing a trap proposed reached a tool
        # without passing the world checks (the intake is the only way).
        for r in cases:
            if not r["trap"]:
                self.assertIn(r["status"], ("passed", "repaired"),
                              r["name"])
            if r["status"] in ("passed", "repaired"):
                self.assertTrue(r["attempts"][-1]["ok"])
            self.assertLessEqual(len(r["attempts"]), 3)
        self.assertLess(meta["spent"], 0.05)
        self.assertTrue(summarize(results)[0].startswith("cases 20"))


if __name__ == "__main__":
    unittest.main()
