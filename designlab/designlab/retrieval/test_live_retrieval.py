"""Live: the small model plans queries and writes cited claims."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveRetrieval(unittest.TestCase):
    def test_model_loop_grounds_and_stays_in_budget(self):
        from .live import run
        lines = run()
        g = lines[2].split("grounded ")[1].split()
        self.assertEqual(g[0], g[2], lines[2])
        top = int(lines[1].split("max ")[1].split(",")[0])
        self.assertLessEqual(top, 8)
        spent = float(lines[-1].split("$")[1])
        self.assertLess(spent, 0.05)


if __name__ == "__main__":
    unittest.main()
