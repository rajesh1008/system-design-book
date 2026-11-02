"""A dense retriever with no dependencies: latent semantic indexing.

TF-IDF vectors are reduced to `dim` dimensions by a randomized SVD
(random projection, two power iterations, then Jacobi on the small
matrix). Documents and queries become unit vectors and are compared by
cosine. It is a stand-in for a learned embedding model: it rewards
shared meaning through co-occurrence and blurs exact identifiers, which
is the behavior the chapter needs from it.
"""
from __future__ import annotations

import math
from collections import Counter

from common.rand import seeded

from .text import tokens


def _orth(cols: list[list[float]]) -> list[list[float]]:
    out = []
    for v in cols:
        w = v[:]
        for u in out:
            d = sum(a * b for a, b in zip(w, u))
            w = [a - d * b for a, b in zip(w, u)]
        n = math.sqrt(sum(a * a for a in w))
        if n > 1e-10:
            out.append([a / n for a in w])
    return out


def _jacobi(m: list[list[float]], sweeps: int = 12):
    """Eigenvalues and eigenvectors (as columns) of a symmetric matrix."""
    n = len(m)
    a = [row[:] for row in m]
    v = [[float(i == j) for j in range(n)] for i in range(n)]
    for _ in range(sweeps):
        off = sum(a[i][j] ** 2 for i in range(n) for j in range(n)
                  if i != j)
        if off < 1e-18:
            break
        for p in range(n - 1):
            for q in range(p + 1, n):
                if abs(a[p][q]) < 1e-14:
                    continue
                th = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = (1 if th >= 0 else -1) / (abs(th)
                                              + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
                for k in range(n):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = v[k][p], v[k][q]
                    v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    return [a[i][i] for i in range(n)], v


class Dense:
    def __init__(self, docs, dim: int = 40, seed: int = 19):
        self.docs = list(docs)
        tf = [Counter(tokens(d.title + " " + d.text)) for d in self.docs]
        df = Counter(t for c in tf for t in c)
        self.vocab = sorted(df)
        self.col = {t: j for j, t in enumerate(self.vocab)}
        n = len(self.docs)
        self.idf = {t: math.log(n / df[t]) + 1 for t in self.vocab}
        rows = []
        for c in tf:
            r = {self.col[t]: (1 + math.log(f)) * self.idf[t]
                 for t, f in c.items()}
            norm = math.sqrt(sum(x * x for x in r.values()))
            rows.append({j: x / norm for j, x in r.items()})
        self.v = self._basis(rows, dim, seed)          # terms x dim
        self.emb = [self._unit(self._project(r)) for r in rows]

    def _basis(self, rows, dim, seed):
        rng = seeded(seed, "retrieval", "dense")
        nt, l = len(self.vocab), dim + 8
        omega = [[rng.gauss(0, 1) for _ in range(l)] for _ in range(nt)]

        def a_times(mat):            # (docs x terms) @ (terms x l)
            return [[sum(x * mat[j][c] for j, x in r.items())
                     for c in range(l)] for r in rows]

        def at_times(y):             # (terms x docs) @ (docs x l)
            out = [[0.0] * l for _ in range(nt)]
            for i, r in enumerate(rows):
                yi = y[i]
                for j, x in r.items():
                    o = out[j]
                    for c in range(l):
                        o[c] += x * yi[c]
            return out

        def cols_orth(y):
            q = _orth([list(col) for col in zip(*y)])
            return [list(r) for r in zip(*q)]

        y = cols_orth(a_times(omega))
        for _ in range(2):
            y = cols_orth(a_times(at_times(y)))
        q = list(zip(*y))                      # l x docs
        b = [[0.0] * nt for _ in q]            # l x terms: Q^T A
        for k, qk in enumerate(q):
            bk = b[k]
            for i, r in enumerate(rows):
                if qk[i]:
                    for j, x in r.items():
                        bk[j] += qk[i] * x
        bbt = [[sum(x * y for x, y in zip(bi, bj)) for bj in b] for bi in b]
        vals, vecs = _jacobi(bbt)
        order = sorted(range(len(vals)), key=lambda i: -vals[i])[:dim]
        basis = []
        for i in order:
            s = math.sqrt(max(vals[i], 1e-12))
            w = [vecs[k][i] for k in range(len(b))]
            basis.append([sum(w[k] * b[k][j] for k in range(len(b))) / s
                          for j in range(nt)])
        return [list(r) for r in zip(*basis)]

    def _project(self, r: dict) -> list[float]:
        dim = len(self.v[0])
        out = [0.0] * dim
        for j, x in r.items():
            vj = self.v[j]
            for c in range(dim):
                out[c] += x * vj[c]
        return out

    @staticmethod
    def _unit(v):
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    def embed(self, text: str) -> list[float]:
        c = Counter(t for t in tokens(text) if t in self.col)
        r = {self.col[t]: (1 + math.log(f)) * self.idf[t]
             for t, f in c.items()}
        return self._unit(self._project(r))

    def search(self, query: str, k: int = 50,
               allow=None) -> list[tuple[int, float]]:
        q = self.embed(query)
        s = [sum(a * b for a, b in zip(q, e)) for e in self.emb]
        idx = [i for i in range(len(s)) if allow is None or allow(i)]
        idx.sort(key=lambda i: (-s[i], i))
        return [(i, s[i]) for i in idx[:k]]
