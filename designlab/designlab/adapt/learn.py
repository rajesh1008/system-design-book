"""TF-IDF and multinomial logistic regression, written out by hand.

The lab's stand-in for a small distilled model: it learns the teacher's
labels from text and reports a probability with every answer, so a low
one can be sent back to the frontier model. Standard library only.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field

from common.rand import seeded

WORD = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    words = WORD.findall(text.lower())
    return words + [f"{a}_{b}" for a, b in zip(words, words[1:])]


@dataclass
class Tfidf:
    min_df: int = 1
    idf: dict[str, float] = field(default_factory=dict)

    def fit(self, texts: list[str]) -> "Tfidf":
        df: Counter = Counter()
        for t in texts:
            df.update(set(tokens(t)))
        n = len(texts)
        self.idf = {w: math.log((1 + n) / (1 + c)) + 1.0
                    for w, c in df.items() if c >= self.min_df}
        return self

    def vector(self, text: str) -> dict[str, float]:
        tf = Counter(w for w in tokens(text) if w in self.idf)
        v = {w: c * self.idf[w] for w, c in tf.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {w: x / norm for w, x in v.items()}


@dataclass
class LogReg:
    epochs: int = 8
    rate: float = 0.5
    l2: float = 1e-4
    seed: int = 17
    classes: list[str] = field(default_factory=list)
    w: dict[str, dict[str, float]] = field(default_factory=dict)
    b: dict[str, float] = field(default_factory=dict)

    def fit(self, X: list[dict[str, float]], y: list[str]) -> "LogReg":
        self.classes = sorted(set(y))
        self.w = {c: {} for c in self.classes}
        self.b = {c: 0.0 for c in self.classes}
        order = list(range(len(X)))
        rng = seeded(self.seed, "adapt", "logreg")
        for epoch in range(self.epochs):
            rng.shuffle(order)
            lr = self.rate / (1 + epoch)
            for i in order:
                p = self.proba(X[i])
                for c in self.classes:
                    g = p[c] - (1.0 if y[i] == c else 0.0)
                    wc = self.w[c]
                    for f, x in X[i].items():
                        wc[f] = wc.get(f, 0.0) * (1 - lr * self.l2) \
                            - lr * g * x
                    self.b[c] -= lr * g
        return self

    def proba(self, x: dict[str, float]) -> dict[str, float]:
        s = {c: self.b[c] + sum(self.w[c].get(f, 0.0) * v
                                for f, v in x.items())
             for c in self.classes}
        top = max(s.values())
        e = {c: math.exp(v - top) for c, v in s.items()}
        z = sum(e.values())
        return {c: v / z for c, v in e.items()}

    def predict(self, x: dict[str, float]) -> tuple[str, float]:
        p = self.proba(x)
        c = max(p, key=p.get)
        return c, p[c]


@dataclass
class Student:
    """TF-IDF features into logistic regression: fit, then predict."""
    vec: Tfidf
    clf: LogReg

    @classmethod
    def train(cls, texts: list[str], labels: list[str],
              seed: int = 17, epochs: int = 8) -> "Student":
        vec = Tfidf().fit(texts)
        X = [vec.vector(t) for t in texts]
        return cls(vec, LogReg(seed=seed, epochs=epochs).fit(X, labels))

    def predict(self, text: str) -> tuple[str, float]:
        return self.clf.predict(self.vec.vector(text))
