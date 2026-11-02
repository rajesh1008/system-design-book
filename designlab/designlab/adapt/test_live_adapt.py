"""Live: the frontier teacher and the small model label 100 messages."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveAdapt(unittest.TestCase):
    def test_teacher_labels(self):
        from adapt.live import run
        lines = run()
        frontier = next(ln for ln in lines if "frontier" in ln)
        right = int(frontier.split("agrees ")[1].split("/")[0])
        # The teacher must be good enough to learn from.
        self.assertGreaterEqual(right, 90)
        spent = float(lines[-1].split("$")[1].split()[0])
        self.assertLess(spent, 0.50)


if __name__ == "__main__":
    unittest.main()
