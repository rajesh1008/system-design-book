"""Score a retrieval configuration against the golden set."""
from __future__ import annotations

from .golden import questions
from .hybrid import search

CONFIGS = {
    "lexical only": dict(method="lexical", dates="off", use_rerank=False),
    "dense only": dict(method="dense", dates="off", use_rerank=False),
    "hybrid": dict(method="hybrid", dates="off", use_rerank=False),
    "hybrid+dates": dict(method="hybrid", dates="pre", use_rerank=False),
    "hybrid+dates+rerank": dict(method="hybrid", dates="pre",
                                use_rerank=True),
    "post-filter+rerank": dict(method="hybrid", dates="post",
                               use_rerank=True),
}


def score(cfg: dict, qs=None, k: int = 10) -> dict:
    qs = qs if qs is not None else questions()
    found = rr = stale1 = short = 0
    for q in qs:
        hits = search(q.text, q.as_of, k=k, **cfg)
        ids = [h.doc.doc_id for h in hits]
        if len(hits) < k:
            short += 1
        if any(i in q.relevant for i in ids):
            found += 1
            first = next(r for r, i in enumerate(ids, 1)
                         if i in q.relevant)
            rr += 1 / first
        if hits and not hits[0].doc.in_effect(q.as_of):
            stale1 += 1
    n = len(qs)
    return {"n": n, "recall": found / n, "mrr": rr / n,
            "stale_at_1": stale1, "short": short}
