"""Live: twelve questions to the model, both paths, under $0.50."""
import unittest

from common.live import skip_unless_live


@skip_unless_live
class TestLiveKnowledge(unittest.TestCase):
    def test_twelve_questions(self):
        import tempfile
        from knowledge.live import run
        with tempfile.TemporaryDirectory() as tmp:   # fresh calls, fixtures
            lines, rows = run(replay=False, cache_dir=tmp)   # untouched
        self.assertEqual(len(rows), 12)
        by = {r["id"]: r for r in rows}
        # A delete never runs, on either path.
        self.assertNotEqual(by["Q12"]["layer"], "answered")
        self.assertNotEqual(by["Q12"]["raw"], "answered")
        spent = float(lines[-1].split("$")[1].split()[0])
        self.assertLess(spent, 0.50)


if __name__ == "__main__":
    unittest.main()
