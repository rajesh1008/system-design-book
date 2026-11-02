"""Retrieval as a component: lexical and dense together, fused by
reciprocal rank, filtered by effective date, optionally reranked, and
returned with provenance.

The contract (section 1 of Chapter 19): every passage returned carries
its source, version, the dates it is in effect, when it was indexed and
why it ranked where it did; nothing out of effect on the case's as-of
date is returned unless the caller asks for history; an empty result is
a result, reported as empty, never padded.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from common.rand import DEFAULT_SEED
from corpus.docs import INDEXED_AT, Doc, documents

from .dense import Dense
from .lexical import BM25
from .rerank import rerank

RRF_K = 60
POOL = 50


@dataclass(frozen=True)
class Hit:
    rank: int
    doc: Doc
    score: float
    why: str            # e.g. "lex 2, dense 5, rerank 1"

    def provenance(self) -> dict:
        d = self.doc
        return {"doc_id": d.doc_id, "version": d.version,
                "source": d.source,
                "effective_from": d.effective_from.isoformat(),
                "effective_to": (d.effective_to.isoformat()
                                 if d.effective_to else None),
                "superseded_by": d.superseded_by,
                "indexed_at": INDEXED_AT, "why": self.why}


@lru_cache(maxsize=4)
def index(seed: int = DEFAULT_SEED):
    docs = documents(seed)
    return docs, BM25(docs), Dense(docs)


def rrf(*rankings: list[tuple[int, float]], k: int = RRF_K) -> dict:
    """Two judges, two scorecards: add 1/(k + rank) from each."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for r, (i, _) in enumerate(ranking, 1):
            fused[i] = fused.get(i, 0.0) + 1.0 / (k + r)
    return fused


def search(query: str, as_of: date | None = None, k: int = 10,
           method: str = "hybrid", dates: str = "pre",
           use_rerank: bool = True, seed: int = DEFAULT_SEED) -> list[Hit]:
    """method: lexical | dense | hybrid. dates: pre | post | off.

    "pre" filters before ranking (only in-effect versions compete);
    "post" ranks everything and then drops what is out of effect from
    the top k, which can return fewer than k; "off" ignores dates.
    """
    docs, bm25, dense = index(seed)
    allow = None
    if dates == "pre" and as_of is not None:
        allow = lambda i: docs[i].in_effect(as_of)       # noqa: E731
    lex = bm25.search(query, POOL, allow) if method != "dense" else []
    den = dense.search(query, POOL, allow) if method != "lexical" else []
    lr = {i: r for r, (i, _) in enumerate(lex, 1)}
    dr = {i: r for r, (i, _) in enumerate(den, 1)}
    fused = rrf(lex, den)
    order = sorted(fused, key=lambda i: (-fused[i], i))
    if use_rerank:
        order = rerank(query, [docs[i] for i in order[:30]], order[:30]) \
            + order[30:]
    if dates == "post" and as_of is not None:
        order = [i for i in order[:k] if docs[i].in_effect(as_of)]
    hits = []
    for r, i in enumerate(order[:k], 1):
        parts = []
        if i in lr:
            parts.append(f"lex {lr[i]}")
        if i in dr:
            parts.append(f"dense {dr[i]}")
        if use_rerank:
            parts.append(f"rerank {r}")
        hits.append(Hit(r, docs[i], round(fused[i], 4), ", ".join(parts)))
    return hits
