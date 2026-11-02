"""Honest evaluation: split by time, check overlap, compare paired.

A random split of messages puts a resend in training and its twin in
the test set; the student remembers the booking reference and the
score goes up for the wrong reason. `overlap` finds that, and `gate`
fails the run before any accuracy is reported.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from common.rand import seeded

from .data import Message


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def first_messages(msgs: list[Message]) -> list[Message]:
    return [m for m in msgs if m.msg_id.endswith("-1")]


def time_split(msgs: list[Message], train: tuple[str, ...],
               val: str, test: str):
    tr = [m for m in msgs if m.month in train]
    va = first_messages([m for m in msgs if m.month == val])
    te = first_messages([m for m in msgs if m.month == test])
    return tr, va, te


def random_split(msgs: list[Message], months: tuple[str, ...],
                 frac: float = 0.8, seed: int = 17):
    pool = [m for m in msgs if m.month in months]
    seeded(seed, "adapt", "random-split").shuffle(pool)
    k = int(len(pool) * frac)
    return pool[:k], pool[k:]


@dataclass
class Overlap:
    test: int
    same_case: int
    same_text: int

    @property
    def case_share(self) -> float:
        return self.same_case / self.test if self.test else 0.0

    @property
    def text_share(self) -> float:
        return self.same_text / self.test if self.test else 0.0


def overlap(train: list[Message], test: list[Message]) -> Overlap:
    cases = {m.case_id for m in train}
    texts = {norm(m.text) for m in train}
    return Overlap(len(test), sum(m.case_id in cases for m in test),
                   sum(norm(m.text) in texts for m in test))


def gate(o: Overlap, max_text_share: float = 0.01) -> list[str]:
    """Reasons the evaluation is invalid; empty means it may be run."""
    why = []
    if o.same_case:
        why.append(f"{o.same_case} test messages share a case with "
                   f"training")
    if o.text_share > max_text_share:
        why.append(f"{o.text_share:.1%} of test text is in training")
    return why


@dataclass
class Score:
    n: int
    right: int
    recall: dict[str, float]

    @property
    def acc(self) -> float:
        return self.right / self.n if self.n else 0.0

    def weakest(self) -> tuple[str, float]:
        k = min(self.recall, key=self.recall.get)
        return k, self.recall[k]


def score(pred: dict[str, str], msgs: list[Message]) -> Score:
    tot: Counter = Counter()
    hit: Counter = Counter()
    for m in msgs:
        tot[m.label] += 1
        hit[m.label] += pred[m.msg_id] == m.label
    return Score(len(msgs), sum(hit.values()),
                 {k: hit[k] / tot[k] for k in tot})


def paired(a: dict[str, str], b: dict[str, str],
           msgs: list[Message]) -> tuple[int, int]:
    """(only a right, only b right): the cases where they differ."""
    only_a = sum(a[m.msg_id] == m.label != b[m.msg_id] for m in msgs)
    only_b = sum(b[m.msg_id] == m.label != a[m.msg_id] for m in msgs)
    return only_a, only_b


def parity(student: Score, frontier: Score, tol: float = 0.005,
           floor: float = 0.90) -> tuple[bool, str]:
    gap = frontier.acc - student.acc
    k, r = student.weakest()
    if gap > tol:
        return False, f"{gap:.1%} below the frontier"
    if r < floor:
        return False, f"{k} recall {r:.0%} under {floor:.0%}"
    return True, f"gap {gap:+.1%}; weakest {k} {r:.0%}"
