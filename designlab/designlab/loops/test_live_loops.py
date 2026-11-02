"""Live: the model writes the hour's report; the trail decides."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveLoops(unittest.TestCase):
    def test_verifier_ignores_the_report(self):
        from loops.live import run, summarize
        res = run()
        self.assertEqual(len(res["refused"]["reports"]), 6)
        self.assertFalse(res["refused"]["verifier"]["green"])
        self.assertFalse(res["counters"]["verifier"]["green"])
        self.assertTrue(res["read"]["verifier"]["green"])
        self.assertLess(res["spent"], 0.05)
        self.assertTrue(summarize(res)[0].startswith("model "))


if __name__ == "__main__":
    unittest.main()
