"""Retrieval drift, made measurable: an index that ages.

An index is a set of documents a crawl has picked up by some date.
Three crawl policies:

    contract   rule and help pages nightly; notices within the
               15-minute contract during an event (same day)
    nightly    everything on the nightly crawl (a page published today
               is searchable tomorrow)
    frozen     nothing after the May 4 re-crawl (the injected failure)

Search is Chapter 19's lexical scorer (retrieval.lexical.BM25) with
the as-of filter (nothing out of effect is a candidate) and the kinds
the request names (waiver questions search notices; the rest search
fare rules). The lab uses
the lexical scorer alone, so its recall sits below Lakeshore's
production numbers; what matters here is how recall moves.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

from corpus.docs import documents
from retrieval.lexical import BM25

FROZEN_AT = date(2026, 5, 4)      # corpus.docs.INDEXED_AT, the re-crawl
GOLDEN_BUILT = date(2026, 5, 8)   # Chapter 19: built May 6 to 8
POLICIES = ("contract", "nightly", "frozen")
KINDS = {"notice": ("notice", "help"),           # the request names
         "rule": ("fare-rule", "help")}           # its kinds (Ch 19)


def published(d) -> date:
    """When a page appeared. Carriers post rule changes three days
    ahead; notices are posted the day they take effect (their effective
    date already sits three days before the event)."""
    if d.kind == "fare-rule" and d.version > 1:
        return d.effective_from - timedelta(days=3)
    return d.effective_from


@lru_cache(maxsize=None)
def _docs():
    docs = documents()
    return docs, BM25(docs)


def indexed(policy: str, as_of: date) -> frozenset:
    """Positions of documents searchable on `as_of` under a policy."""
    docs, _ = _docs()
    out = set()
    for i, d in enumerate(docs):
        p = published(d)
        if policy == "frozen":
            ok = p <= FROZEN_AT
        elif policy == "nightly":
            ok = p < as_of
        elif policy == "contract":
            ok = p <= as_of if d.kind == "notice" else p < as_of
        else:
            raise ValueError(policy)
        if ok:
            out.add(i)
    return frozenset(out)


def hit(question, policy: str, k: int = 10) -> bool:
    """Is a relevant passage in the top k for this question?"""
    docs, bm = _docs()
    idx = indexed(policy, question.as_of)
    kinds = KINDS["notice" if question.style == "notice" else "rule"]
    allow = (lambda i: i in idx and docs[i].kind in kinds
             and docs[i].in_effect(question.as_of))
    top = bm.search(question.text, k, allow)
    ids = {docs[i].doc_id for i, _ in top}
    return any(r in ids for r in question.relevant)


def recall(questions, policy: str, k: int = 10) -> tuple[float, list]:
    """(recall at k in percent, the questions that missed)."""
    missed = [q for q in questions if not hit(q, policy, k)]
    n = len(questions)
    return (100.0 * (n - len(missed)) / n if n else 0.0), missed
