"""Tests for the Chapter 47 bank extension. Offline.

Tests that read the manuscript skip when it is absent (the public
repository carries the committed index snapshot instead).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from . import appendix, loop, sides
from .manuscript import ROOT, SNAPSHOT, available, load_snapshot, scan
from .rounds import route
from .schema import BankError, Question
from .taxonomy import LOOP_FORMATS, ROUNDS, TIER_LEVEL

HAVE_MS = available(ROOT)

ONE = """## Interview Questions and Answers {.interview}

:::: {.qa type="concept" round="system-design" level="senior"}
**Q99.1 Where does permission live?**

**Outside the model.** The policy engine decides.
{pad}

::: weak
A weak answer says the model decides.
:::
::::
"""
ONE = ONE.replace("{pad}", " ".join(["The rule is signed."] * 40))
ONE = ONE.replace("Q99.1", "Q47.1")


def row(qid="Q1.1", ch=1, tag="system-design", level="staff",
        hs=False):
    return {"qid": qid, "chapter": ch, "type": "design", "round": tag,
            "level": level, "loop_round": tag, "rule": "declared",
            "hiring_side": hs, "answer_words": 200, "weak_line": True}


class TestTaxonomy(unittest.TestCase):
    def test_seven_formats_nine_tags(self):
        self.assertEqual(len(LOOP_FORMATS), 7)
        self.assertEqual(len(ROUNDS), 9)
        self.assertTrue(set(LOOP_FORMATS) <= set(ROUNDS))

    def test_mid_tier_maps_to_l3(self):
        self.assertEqual(TIER_LEVEL["mid"], "L3")


class TestRouter(unittest.TestCase):
    def q(self, **kw):
        base = dict(qid="Q31.2", chapter=31, type="design",
                    round="system-design", level="staff",
                    text="Design the gateway.")
        base.update(kw)
        return Question(**base)

    def test_declared_tag_kept(self):
        r = route(self.q(round="evaluation-operations"))
        self.assertEqual((r.tag, r.rule),
                         ("evaluation-operations", "declared"))

    def test_hiring_side_wins_over_keywords(self):
        r = route(self.q(text="From the hiring side, review a policy."))
        self.assertEqual(r.tag, "hiring-manager")

    def test_part_fallback(self):
        self.assertEqual(route(self.q(text="Draw it.")).tag,
                         "control-plane-security")


class TestScanAndIndex(unittest.TestCase):
    def test_extra_chapter_is_scanned(self):
        with tempfile.TemporaryDirectory() as d:
            s = scan(Path(d), extra={47: ONE})
        self.assertEqual([q.qid for q in s.questions], ["Q47.1"])
        self.assertEqual(s.problems(), [])

    def test_question_with_no_chapter_fails(self):
        broken = ONE.replace("**Q47.1 ", "**")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(BankError) as cm:
                appendix.rows(Path(d), extra={47: broken})
        self.assertTrue(any("chapter" in p for p in cm.exception.problems))

    def test_render_never_repeats_an_answer(self):
        with tempfile.TemporaryDirectory() as d:
            rs = appendix.rows(Path(d), extra={47: ONE})
        md = appendix.render(rs)
        self.assertIn("Q47.1", md)
        self.assertNotIn("policy engine decides", md)

    def test_card_counts_short_chapters(self):
        rs = [row("Q1.1", 1, hs=True), row("Q1.2", 1, hs=True),
              row("Q2.1", 2, hs=True), row("Q2.2", 2)]
        c = appendix.card(rs)
        self.assertEqual(c["hiring_side"], 3)
        self.assertEqual(c["hiring_short"], [2])
        self.assertFalse(c["target_met"])

    def test_snapshot_round_trip(self):
        rs = [row(), row("Q1.2", hs=True)]
        with tempfile.TemporaryDirectory() as d:
            from .manuscript import snapshot
            p = snapshot(rs, Path(d) / "i.tsv")
            back = load_snapshot(p)
        self.assertEqual([r["qid"] for r in back], ["Q1.1", "Q1.2"])
        self.assertEqual([r["hiring_side"] for r in back], [False, True])


class TestCommittedSnapshot(unittest.TestCase):
    def test_snapshot_meets_the_floor(self):
        c = appendix.card(load_snapshot(SNAPSHOT))
        self.assertGreaterEqual(c["questions"], appendix.TARGET)
        self.assertEqual(c["chapters"], appendix.CHAPTERS)
        self.assertEqual(c["tags"], 9)

    def test_snapshot_has_no_question_text(self):
        header = SNAPSHOT.read_text(encoding="utf-8").splitlines()[0]
        self.assertNotIn("text", header.split("\t"))

    @unittest.skipUnless(HAVE_MS, "manuscript not present")
    def test_snapshot_matches_manuscript(self):
        live = appendix.rows(ROOT)
        snap = load_snapshot(SNAPSHOT)
        self.assertEqual([(r["qid"], r["loop_round"]) for r in live],
                         [(r["qid"], r["loop_round"]) for r in snap])


class TestLoop(unittest.TestCase):
    def test_tiers_one_rung_up(self):
        self.assertEqual(loop.tiers_for("staff"), ("staff", "principal"))
        self.assertEqual(loop.tiers_for("principal"), ("principal",))

    def test_questions_per_round(self):
        self.assertEqual(loop.per_round(45), 2)
        self.assertEqual(loop.per_round(30), 1)
        self.assertEqual(loop.per_round(15), 1)

    def test_plan_is_reproducible_and_seeded(self):
        rs = [row(f"Q1.{i}", 1) for i in range(1, 30)]
        a = loop.plan(rs, ["system-design"], "staff", seed="x")
        b = loop.plan(rs, ["system-design"], "staff", seed="x")
        c = loop.plan(rs, ["system-design"], "staff", seed="y")
        self.assertEqual(a[0].questions, b[0].questions)
        self.assertNotEqual(a[0].questions, c[0].questions)

    def test_staff_loop_is_four_to_six_hours(self):
        cfg = loop.config()
        role = cfg["roles"]["staff"]
        rs = load_snapshot(SNAPSHOT)
        planned = loop.plan(rs, role["rounds"], role["tier"])
        final = loop.total(planned) - planned[0].round.minutes
        self.assertTrue(240 <= final <= 360)


class TestSides(unittest.TestCase):
    def test_one_candidate_never_names_the_policy_engine(self):
        _, heard = sides.read()
        named = {h.candidate: h.named_policy for h in heard}
        self.assertEqual(named, {"V07": False, "V19": True})

    def test_unknown_listen_item_is_an_error(self):
        with self.assertRaises(ValueError):
            sides.hear({"id": "X", "said": [
                {"at": 1, "text": "t", "shows": ["vibes"]}]},
                {"permission": "p"})


if __name__ == "__main__":
    unittest.main()
