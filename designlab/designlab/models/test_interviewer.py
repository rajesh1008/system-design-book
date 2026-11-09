"""Chapter 46: the mock interviewer's contract, replayed offline."""
from __future__ import annotations

import unittest

from ladder import notes
from ladder.drill import run
from models import interviewer


class TestInterviewer(unittest.TestCase):
    def test_contract(self):
        pin = "claude-haiku-5-5"
        self.assertEqual(interviewer.check("Who grants it?", pin, pin), [])
        long = " ".join(["word"] * 31) + "?"
        self.assertIn("31 words, over 30",
                      interviewer.check(long, pin, pin))
        self.assertIn("not a question",
                      interviewer.check("Tell me.", pin, pin))
        self.assertTrue(interviewer.check("Ok?", "other", pin))

    def test_drill_replays_and_every_question_passes(self):
        rows = run(notes.load("A03b"))
        asked = [r for r in rows if r["question"]]
        self.assertEqual([r["gap"] for r in asked],
                         ["G1", "G2", "G3", "G5"])
        for r in asked:
            self.assertEqual(r["model"], "claude-haiku-5-5")
            self.assertEqual(
                interviewer.check(r["question"], r["model"],
                                  "claude-haiku-5-5"), [])
            self.assertIn(r["source"], ("model", "repair", "checklist"))

    def test_fallback_is_the_checklist_wording(self):
        rows = run(notes.load("A03b"))
        fall = [r for r in rows if r["source"] == "checklist"]
        for r in fall:
            self.assertEqual(r["question"],
                             interviewer.GAP_QUESTIONS[r["gap"]])


if __name__ == "__main__":
    unittest.main()
