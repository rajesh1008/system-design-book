"""The Chapter 17 lab pipeline, shared by the demo and the tests."""
from __future__ import annotations

from dataclasses import dataclass

from . import evaluate as E
from .data import Message, generate
from .learn import Student
from .teacher import sim_teacher

TRAIN = ("2025-12", "2026-01", "2026-02", "2026-03")
VAL, TEST = "2026-04", "2026-05"
NEW_TYPE = {"group_split": ("2026-05", [
    "take one traveler off our group booking",
    "remove my colleague from the group reservation",
    "split my son off the family booking, he is not going",
], 40)}


@dataclass
class Run:
    train: list[Message]
    val: list[Message]
    test: list[Message]
    teacher: dict[str, str]
    student: Student
    tau: float
    stu: dict[str, str]          # student alone on the test month
    cas: dict[str, str]          # student, escalating below tau
    fr: dict[str, str]           # frontier teacher on the test month
    escalated: float


def cascade(s: Student, msgs, teacher, tau):
    out, esc = {}, 0
    for m in msgs:
        lab, p = s.predict(m.text)
        if p < tau:
            esc += 1
            lab = teacher[m.msg_id]
        out[m.msg_id] = lab
    return out, esc / len(msgs) if msgs else 0.0


def pick_tau(s: Student, val, teacher, grid=(0.3, 0.4, 0.5, 0.6, 0.7)):
    """Smallest threshold at which the cascade matches the frontier on
    the validation month; the test month is never looked at."""
    f = E.score({m.msg_id: teacher[m.msg_id] for m in val}, val).acc
    for tau in grid:
        c, _ = cascade(s, val, teacher, tau)
        if E.score(c, val).acc >= f:
            return tau
    return grid[-1]


FLOOR = 0.5        # escalate when the student is under even money


def run(seed: int = 17, half: bool = False, new_type: bool = False,
        train_months=TRAIN, val=VAL, test=TEST,
        tau: float | None = FLOOR) -> Run:
    """tau=None tunes the threshold on the validation month instead."""
    msgs = generate(seed, extra_types=NEW_TYPE if new_type else None)
    teacher = sim_teacher(msgs, seed)
    tr, va, te = E.time_split(msgs, train_months, val, test)
    if half:
        cases = sorted({m.case_id for m in tr})[::2]
        keep = set(cases)
        tr = [m for m in tr if m.case_id in keep]
    s = Student.train([m.text for m in tr],
                      [teacher[m.msg_id] for m in tr], seed)
    if tau is None:
        tau = pick_tau(s, va, teacher)
    stu = {m.msg_id: s.predict(m.text)[0] for m in te}
    cas, esc = cascade(s, te, teacher, tau)
    fr = {m.msg_id: teacher[m.msg_id] for m in te}
    return Run(tr, va, te, teacher, s, tau, stu, cas, fr, esc)


def leaky(seed: int = 17):
    """The injected failure: a random split of the training months."""
    msgs = generate(seed)
    teacher = sim_teacher(msgs, seed)
    tr, te = E.random_split(msgs, TRAIN, seed=seed)
    s = Student.train([m.text for m in tr],
                      [teacher[m.msg_id] for m in tr], seed)
    pred = {m.msg_id: s.predict(m.text)[0] for m in te}
    return tr, te, E.score(pred, te), E.overlap(tr, te)
