"""BM25 over the document corpus. Exact words, carrier codes and rule
references are what it is good at."""
from __future__ import annotations

import math
from collections import Counter

from .text import tokens


class BM25:
    def __init__(self, docs, k1: float = 1.2, b: float = 0.75):
        self.docs = list(docs)
        self.k1, self.b = k1, b
        self.tf = [Counter(tokens(d.title + " " + d.text))
                   for d in self.docs]
        self.len = [sum(c.values()) for c in self.tf]
        self.avg = sum(self.len) / len(self.len)
        df = Counter(t for c in self.tf for t in c)
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5))
                    for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokens(query)
        out = []
        for c, ln in zip(self.tf, self.len):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * ln / self.avg)
            for t in q:
                f = c.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def search(self, query: str, k: int = 50,
               allow=None) -> list[tuple[int, float]]:
        s = self.scores(query)
        idx = [i for i in range(len(s)) if allow is None or allow(i)]
        idx.sort(key=lambda i: (-s[i], i))
        return [(i, s[i]) for i in idx[:k] if s[i] > 0]
