"""A reranker stand-in. It reads the query and each candidate together,
as a cross-encoder does, and scores what a bag of words cannot: does the
passage belong to the carrier the query names, is it about the topic the
query describes (in the customer's words or the rule's), and does it
cover the fare product asked about. Deterministic, so the lab's numbers
repeat; a production reranker is a model, with a latency and a price.
"""
from __future__ import annotations

from corpus.docs import CARRIERS, NOTICE_EVENTS, PRODUCTS, TOPICS

from .text import tokens

_NAMES = {code: set(tokens(name)) - {"air", "airway", "airline", "jet",
                                      "wing", "express"}
          for code, name in CARRIERS}
_TOPIC_WORDS = {}
for _t, (_title, _words, _says) in TOPICS.items():
    _TOPIC_WORDS[_t] = set(tokens(_title))
    for _s in _says:
        _TOPIC_WORDS[_t] |= set(tokens(_s))
_AIRPORTS = {e[0] for e in NOTICE_EVENTS}
_GENERIC = set(tokens("flight ticket trip booking airline day travel "
                      "fare pay what fee change"))
for _t in _TOPIC_WORDS:
    _TOPIC_WORDS[_t] -= _GENERIC


def query_carrier(q: str) -> str | None:
    qt = set(tokens(q))
    for code, name in _NAMES.items():
        if code.lower() in qt or name & qt:
            return code
    return None


def query_topic(q: str) -> str | None:
    qt = set(tokens(q))
    if "waiver" in qt:
        apt = [w.upper() for w in qt if w.upper() in _AIRPORTS]
        return f"waiver-{apt[0]}" if apt else "waiver"
    best, score = None, 0
    for t, words in _TOPIC_WORDS.items():
        s = len(words & qt)
        if s > score:
            best, score = t, s
    return best


def score(q: str, doc) -> float:
    s = 0.0
    c, t = query_carrier(q), query_topic(q)
    if c and doc.carrier == c:
        s += 2.0
    elif c and doc.carrier:
        s -= 1.0
    if t and doc.topic and (doc.topic == t or (
            t == "waiver" and doc.topic.startswith("waiver"))):
        s += 1.5
    if doc.kind == "fare-rule" and c:
        s += 0.5
    if any(p.lower() in q.lower() for p in PRODUCTS) and \
            doc.kind == "fare-rule":
        s += 0.25
    return s


def rerank(q: str, docs: list, ids: list[int]) -> list[int]:
    scored = [(score(q, d), -n, i) for n, (d, i) in
              enumerate(zip(docs, ids))]
    scored.sort(reverse=True)
    return [i for _, _, i in scored]
