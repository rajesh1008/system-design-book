"""Tests for the interview bank v0. Offline."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bank import (LEVELS, ROUNDS, TYPES, BankError, Question, load,
                  parse_markup, parse_table, reconcile, render, validate)
from bank.index import main as index_main

FIX = Path(__file__).with_name("fixtures")
REFERENCE = (Path(__file__).resolve().parents[3] / "02-manuscript"
             / "interview-voice-reference.md")


def q(**kw) -> Question:
    base = dict(qid="Q2.1", chapter=2, type="concept",
                round="system-design", level="L4", text="Why?")
    base.update(kw)
    return Question(**base)


class TestTaxonomy(unittest.TestCase):
    def test_vocabularies(self):
        self.assertEqual(list(TYPES.values()), ["C", "S", "T", "K"])
        self.assertEqual(len(LEVELS), 7)
        prompt_rounds = {"phone-screen", "system-design",
                         "distributed-systems", "agent-runtime",
                         "control-plane-security", "evaluation-operations",
                         "take-home", "bar-raiser"}
        self.assertLessEqual(prompt_rounds, set(ROUNDS))


class TestValidate(unittest.TestCase):
    def test_good_question_passes(self):
        self.assertEqual(validate([q()]), [])

    def test_question_with_no_chapter_fails(self):
        self.assertIn("no chapter", validate([q(chapter=None)])[0])

    def test_unknown_values_fail(self):
        self.assertEqual(len(validate([q(type="trivia", round="lunch",
                                         level="L9", methods=["vibes"])])),
                         4)

    def test_id_shape_and_agreement(self):
        self.assertTrue(validate([q(qid="2.1")]))
        self.assertTrue(validate([q(qid="Q3.1")]))

    def test_duplicates_fail(self):
        self.assertIn("duplicate", validate([q(), q()])[0])

    def test_answer_shape_is_optional(self):
        short = q(answer_words=40, weak_line=False)
        self.assertEqual(validate([short]), [])
        self.assertEqual(len(validate([short], answers=True)), 2)


class TestLoaders(unittest.TestCase):
    def test_table_fixture(self):
        qs = load(FIX / "sample-bank.md")
        self.assertEqual(len(qs), 10)
        self.assertEqual({x.type for x in qs}, set(TYPES))
        q71 = next(x for x in qs if x.qid == "Q7.1")
        self.assertEqual(q71.competency, ["effects", "idempotency"])
        self.assertEqual(q71.chapter, 7)

    def test_markup_fixture(self):
        qs = load(FIX / "sample-chapter.md")
        self.assertEqual([x.qid for x in qs], ["Q1.1", "Q4.2", "Q41.2"])
        self.assertEqual(qs[2].type, "stakeholder")   # from the K alias
        self.assertEqual(qs[1].methods, ["estimation-sheet"])
        self.assertTrue(qs[0].weak_line)
        self.assertFalse(qs[1].weak_line)

    def test_unclosed_block_fails(self):
        with self.assertRaises(BankError):
            parse_markup(':::: {.qa type="concept"}\n**Q1.1 Why?**\n')

    def test_load_raises_on_bad_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.md"
            p.write_text("| ID | Chapter | Type | Round | Level |"
                         " Question |\n|---|---|---|---|---|---|\n"
                         "| Q5.1 | | C | phone-screen | L3 | Why? |\n")
            with self.assertRaises(BankError) as ctx:
                load(p)
            self.assertIn("no chapter", ctx.exception.problems[0])

    @unittest.skipUnless(REFERENCE.exists(), "manuscript not present")
    def test_interview_voice_reference_parses(self):
        qs = load(REFERENCE)
        self.assertGreaterEqual(len(qs), 3)
        self.assertEqual(validate(qs, answers=True), [])


class TestIndex(unittest.TestCase):
    def test_render_groups_and_points_to_chapters(self):
        md = render(load(FIX / "sample-bank.md"))
        self.assertIn("### Bar-raiser conversation", md)
        self.assertIn("- Q7.1 (T, L5): Chapter 7", md)
        self.assertNotIn("weak answer", md.lower())

    def test_render_refuses_a_question_with_no_chapter(self):
        with self.assertRaises(BankError):
            render([q(chapter=None)])

    def test_reconcile(self):
        bank = load(FIX / "sample-bank.md")
        chapter = load(FIX / "sample-chapter.md")
        problems = reconcile(chapter, bank)
        self.assertEqual(len(problems), 2)
        self.assertTrue(all("level" in p for p in problems))
        self.assertIn("missing", reconcile([q(qid="Q2.9")], bank)[0])

    def test_cli_exit_codes(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(index_main([str(FIX / "sample-bank.md")]), 0)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.md"
            p.write_text("| ID | Chapter | Type | Round | Level |"
                         " Question |\n|---|---|---|---|---|---|\n"
                         "| Q5.1 | | C | phone-screen | L3 | Why? |\n")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(index_main([str(p)]), 1)


if __name__ == "__main__":
    unittest.main()
