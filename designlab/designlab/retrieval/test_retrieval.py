"""Chapter 19 offline tests: the corpus, the ranking stack, the golden
set, provenance, the agentic loop and its budget.

RETRIEVAL_INJECT=no-stop runs TestBudget against the loop with its
verifier and budget removed; that run is meant to fail.
"""
from __future__ import annotations

import os
import unittest
from datetime import date

from corpus.docs import by_id, documents, in_effect

from . import agentic, grounding, hybrid
from .demo import ISSUED, OPENING_Q
from .evaluate import CONFIGS, score
from .golden import questions
from .tasks import RUNAWAY, tasks

INJECT = os.environ.get("RETRIEVAL_INJECT") or None


class TestCorpus(unittest.TestCase):
    def test_deterministic(self):
        a = [d.doc_id for d in documents()]
        self.assertEqual(len(a), len(set(a)))
        self.assertEqual(a, [d.doc_id for d in documents()])

    def test_opening_versions(self):
        old, cur = by_id()["FR-XPA-same-day-v1"], by_id()["FR-XPA-same-day-v2"]
        self.assertEqual(old.facts["Main"], "75")
        self.assertEqual(cur.facts["Main"], "100")
        self.assertEqual(old.superseded_by, cur.doc_id)
        self.assertFalse(old.in_effect(ISSUED))
        self.assertTrue(cur.in_effect(ISSUED))

    def test_one_version_in_effect(self):
        day = date(2026, 5, 4)
        for d in documents():
            if d.kind == "fare-rule":
                same = [x for x in documents() if x.kind == "fare-rule"
                        and x.carrier == d.carrier
                        and x.topic == d.topic and x.in_effect(day)]
                self.assertEqual(len(same), 1, d.doc_id)
                self.assertEqual(in_effect(d.carrier, d.topic, day).doc_id,
                                 same[0].doc_id)


class TestRanking(unittest.TestCase):
    def test_pilot_ranks_superseded_first(self):
        hits = hybrid.search(OPENING_Q, ISSUED, k=5, method="dense",
                             dates="off", use_rerank=False)
        self.assertEqual(hits[0].doc.doc_id, "FR-XPA-same-day-v1")
        ids = [h.doc.doc_id for h in hits]
        self.assertEqual(ids.index("FR-XPA-same-day-v2"), 3)

    def test_full_pipeline_ranks_current_first(self):
        hits = hybrid.search(OPENING_Q, ISSUED, k=5)
        self.assertEqual(hits[0].doc.doc_id, "FR-XPA-same-day-v2")
        self.assertTrue(all(h.doc.in_effect(ISSUED) for h in hits))

    def test_provenance_fields(self):
        p = hybrid.search(OPENING_Q, ISSUED, k=1)[0].provenance()
        for key in ("doc_id", "version", "source", "effective_from",
                    "effective_to", "superseded_by", "indexed_at", "why"):
            self.assertIn(key, p)
        self.assertTrue(p["indexed_at"].endswith("-05:00"))

    def test_rrf_rewards_agreement(self):
        # Each list is (doc index, score), best first. Doc 2 is second
        # in both; doc 1 and doc 3 each top one list and miss the other.
        fused = hybrid.rrf([(1, .9), (2, .8)], [(3, .9), (2, .7)])
        self.assertEqual(max(fused, key=fused.get), 2)


class TestGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qs = questions()
        cls.r = {n: score(c, cls.qs) for n, c in CONFIGS.items()}

    def test_size(self):
        self.assertEqual(len(self.qs), 350)

    def test_hybrid_beats_either_alone(self):
        r = self.r
        self.assertGreater(r["hybrid"]["recall"], r["dense only"]["recall"])
        self.assertGreater(r["dense only"]["recall"],
                           r["lexical only"]["recall"])

    def test_date_filter_removes_stale_rank_one(self):
        self.assertGreater(self.r["hybrid"]["stale_at_1"], 0)
        self.assertEqual(self.r["hybrid+dates"]["stale_at_1"], 0)

    def test_reranker_lifts_recall(self):
        self.assertGreaterEqual(self.r["hybrid+dates+rerank"]["recall"],
                                0.95)

    def test_post_filter_returns_short_lists(self):
        self.assertGreater(self.r["post-filter+rerank"]["short"], 0)
        self.assertEqual(self.r["hybrid+dates+rerank"]["short"], 0)


class TestLoop(unittest.TestCase):
    def test_verified_citations_ground(self):
        runs = [agentic.run(t) for t in tasks()]
        g, n = grounding.rate(runs)
        self.assertEqual(g, n)
        self.assertTrue(all(r.handed_off for r in runs
                            if not r.task.answerable))

    def test_citing_what_was_read_cites_notes(self):
        runs = [agentic.run(t, use_rerank=False, cite="read")
                for t in tasks()]
        verdicts = [v for r in runs
                    for _, _, v in grounding.check(r.task, r.answer)]
        self.assertIn("cites a note", verdicts)

    def test_dates_off_cites_superseded(self):
        runs = [agentic.run(t, dates="off", cite="read") for t in tasks()]
        verdicts = [v for r in runs
                    for _, _, v in grounding.check(r.task, r.answer)]
        self.assertIn("not in effect", verdicts)

    def test_runaway_without_stop(self):
        r = agentic.run(RUNAWAY, inject="no-stop")
        self.assertEqual(len(r.queries), 41)
        self.assertEqual(agentic.run(RUNAWAY).stop, "budget")


class TestBudget(unittest.TestCase):
    """No task issues more than eight queries. Fails under inject."""

    def test_budget_holds(self):
        runs = [agentic.run(t, inject=INJECT) for t in tasks()]
        runs.append(agentic.run(RUNAWAY, inject=INJECT))
        fails = agentic.check_budget(runs, 8)
        self.assertEqual(fails, [], f"{len(fails)} over: {fails[:2]}")


if __name__ == "__main__":
    unittest.main()
