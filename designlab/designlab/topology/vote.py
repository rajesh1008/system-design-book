"""Voting, debate, and one agent with a verifier (Chapter 27), offline.

Twenty-four eligibility tasks, each run 25 times per design: 600 runs
a design. The voters are the same model reading the same rule card,
so their errors are correlated: with probability RHO a voter makes
the run's shared mistake, if there is one, instead of an independent
one. That is the whole argument in one parameter; set RHO to 0 and
voting looks much better than it is in practice.

designs
  single     one answer
  verifier   one answer, checked by eligibility.verify; on a finding,
             one repair with the finding; still failing, to the desk
  vote       three answers, majority; three different answers, desk
  debate     the three answers, then a second round in which each
             voter sees the others; majority of round two

Outcomes per run: correct, desk (a person decides, no effect), or
wrong (a wrong yes or no that would have been acted on).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common.rand import seeded

from .eligibility import QUESTION, RULES, TASKS, Task, truth

REPEATS = 25
RHO = 0.65
EASY_ERROR = 0.03
TRAP_ERROR = 0.20
REPAIR_OK = 0.60
SWITCH_TO_MAJORITY = 0.70     # a minority voter gives in (round two)
DRIFT = 0.04                  # a correct voter talks itself out of it
FIXED = 0.10                  # a wrong voter is talked out of it
OUT_TOKENS = 40
VERDICTS = ("yes", "no", "desk")


def tokens_of(text: str) -> int:
    return max(1, len(text) // 4)


def base_input(t: Task) -> int:
    return tokens_of(RULES) + tokens_of(t.record()) + tokens_of(QUESTION)


def _wrong(right: str, rng) -> str:
    others = [v for v in VERDICTS if v != right]
    # most wrong answers are the trap's wrong answer
    return others[0] if rng.random() < 0.85 else others[1]


def _error_rate(t: Task) -> float:
    return TRAP_ERROR if t.trap else EASY_ERROR


def _voters(t: Task, rng, n: int) -> list[str]:
    right, _ = truth(t)
    e = _error_rate(t)
    shared = _wrong(right, rng) if rng.random() < e else right
    out = []
    for _ in range(n):
        if rng.random() < RHO:
            out.append(shared)
        else:
            out.append(_wrong(right, rng) if rng.random() < e else right)
    return out


def _majority(vs: list[str]) -> str:
    best = max(set(vs), key=vs.count)
    return best if vs.count(best) >= 2 else "desk"


def _outcome(t: Task, verdict: str) -> str:
    right, _ = truth(t)
    if verdict == right:
        return "correct"
    return "desk" if verdict == "desk" else "wrong"


@dataclass
class DesignResult:
    design: str
    runs: int = 0
    correct: int = 0
    desk: int = 0
    wrong: int = 0
    tokens: int = 0
    calls: int = 0
    by_task: dict[str, int] = field(default_factory=dict)

    @property
    def success(self) -> float:
        return self.correct / self.runs


def run(design: str, t: Task, rng) -> tuple[str, int, int]:
    """(outcome, tokens, calls) for one run."""
    base = base_input(t) + OUT_TOKENS
    if design == "single":
        return _outcome(t, _voters(t, rng, 1)[0]), base, 1
    if design == "verifier":
        v = _voters(t, rng, 1)[0]
        right, _ = truth(t)
        caught = v != right and not t.claim     # the verifier's gap
        if not caught:
            return _outcome(t, v), base, 1
        repair = base + OUT_TOKENS + 30          # answer and finding
        if rng.random() < REPAIR_OK:
            return "correct", base + repair, 2
        return "desk", base + repair, 2
    if design == "vote":
        return _outcome(t, _majority(_voters(t, rng, 3))), 3 * base, 3
    if design == "debate":
        r1 = _voters(t, rng, 3)
        right, _ = truth(t)
        maj = _majority(r1)
        r2 = []
        for v in r1:
            if v != maj and maj != "desk" and \
                    rng.random() < SWITCH_TO_MAJORITY:
                v = maj
            if v == right and rng.random() < DRIFT:
                v = _wrong(right, rng)
            elif v != right and rng.random() < FIXED:
                v = right
            r2.append(v)
        round2 = base + 3 * OUT_TOKENS + 40
        return (_outcome(t, _majority(r2)), 3 * base + 3 * round2, 6)
    raise ValueError(design)


DESIGNS = ("single", "verifier", "vote", "debate")


def trial(design: str, seed: int = 27, rho: float | None = None
          ) -> DesignResult:
    global RHO
    saved = RHO
    if rho is not None:
        RHO = rho
    try:
        res = DesignResult(design)
        for t in TASKS:
            for k in range(REPEATS):
                rng = seeded(seed, "vote", design, t.task_id, str(k))
                o, tok, calls = run(design, t, rng)
                res.runs += 1
                res.tokens += tok
                res.calls += calls
                setattr(res, o, getattr(res, o) + 1)
                if o == "correct":
                    res.by_task[t.task_id] = \
                        res.by_task.get(t.task_id, 0) + 1
        return res
    finally:
        RHO = saved


def table(seed: int = 27, rho: float | None = None) -> list[DesignResult]:
    return [trial(d, seed, rho) for d in DESIGNS]
