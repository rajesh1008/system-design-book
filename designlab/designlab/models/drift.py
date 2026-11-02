"""Drift: notice when the thing behind a model ID changes (Chapter 13).

A baseline is what one contract run looked like when the contract was
last accepted: the echoed model ID, how many golden cases passed, and the
key set of every output. A later run is compared with it, and each
difference becomes an alert addressed to the contract's alert_to.

  echo-drift      the provider says a different model answered
  behavior-drift  fewer golden answers are right than at the baseline
  budget-drift    calls exceed the contract's cost or latency bound
  shape-drift     an output's key set or a value's form changed

The transports below simulate the two ways a model moves under a fixed
name, for the offline demo: loudly (the echo changes) and silently (the
echo stays, the outputs change shape). A third, real one is recorded
live: an alias whose target is repointed to a newer model.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .contract import ModelContract, parse_json
from .runner import SuiteResult


BUDGET = ("dear", "slow")
NOT_BEHAVIOR = ("echo-drift",) + BUDGET


def behaved(r: SuiteResult) -> int:
    """Cases whose answers were right and well formed, whoever answered
    and whatever it cost. Echo and budget have alerts of their own."""
    return sum(all(v.code in NOT_BEHAVIOR for v in x.violations)
               for x in r.cases)


def _shape(output_text: str | None) -> str:
    obj = parse_json(output_text or "")
    if obj is None:
        return "not-json"
    return ",".join(sorted(obj))


@dataclass(frozen=True)
class Baseline:
    contract: str
    version: str
    prompt: str
    echo: str
    passed: int
    total: int
    shapes: dict = field(default_factory=dict)   # case -> key signature

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True, indent=1)

    @staticmethod
    def from_json(text: str) -> "Baseline":
        return Baseline(**json.loads(text))


def baseline(c: ModelContract, r: SuiteResult) -> Baseline:
    echoes = sorted(r.echoes)
    return Baseline(c.name, c.version, c.prompt_hash, ",".join(echoes),
                    behaved(r), len(r.cases),
                    {x.case_id: _shape(x.raw) for x in r.cases})


@dataclass(frozen=True)
class Alert:
    code: str
    contract: str
    detail: str
    to: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


def compare(c: ModelContract, base: Baseline, r: SuiteResult
            ) -> list[Alert]:
    alerts = []
    echo = ",".join(sorted(r.echoes))
    if echo != base.echo:
        alerts.append(Alert("echo-drift", c.name,
                            f"was {base.echo}, now {echo}", c.alert_to))
    ok = behaved(r)
    if ok < base.passed:
        alerts.append(Alert("behavior-drift", c.name,
                            f"{ok}/{len(r.cases)} answers right, "
                            f"was {base.passed}/{base.total}",
                            c.alert_to))
    over = sum(any(v.code in BUDGET for v in x.violations)
               for x in r.cases)
    if over:
        alerts.append(Alert("budget-drift", c.name,
                            f"{over} calls over the cost or latency "
                            f"bound", c.alert_to))
    moved = [x.case_id for x in r.cases
             if base.shapes.get(x.case_id) not in (None, _shape(x.raw))]
    if moved:
        alerts.append(Alert("shape-drift", c.name,
                            f"{len(moved)} outputs changed form",
                            c.alert_to))
    return alerts


# --- simulated moves, for offline demos and tests -----------------------

class LoudMove:
    """The echo changes: the provider reports a different model."""

    def __init__(self, inner, new_id: str = "claude-haiku-x-injected"):
        self.inner, self.new_id = inner, new_id

    def __call__(self, body):
        resp = dict(self.inner(body))
        resp["model"] = self.new_id
        return resp


class SilentMove:
    """The echo stays; the outputs change form. Codes come back title
    cased with spaces, and a new key appears. Nothing here is a crash."""

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, body):
        resp = json.loads(json.dumps(self.inner(body)))
        for block in resp.get("content", []):
            if block.get("type") != "text":
                continue
            obj = parse_json(block["text"])
            if obj is None:
                continue
            if isinstance(obj.get("reason_code"), str):
                obj["reason_code"] = (obj["reason_code"]
                                      .replace("_", " ").title())
            obj["confidence"] = 0.93
            block["text"] = json.dumps(obj)
        return resp


class Repoint:
    """Live: sends the request to a different model ID than the caller
    asked for, the way an alias does when its target moves. The request
    the client records still names the alias, as the caller's did."""

    def __init__(self, inner, to_id: str):
        self.inner, self.to_id = inner, to_id

    def __call__(self, body):
        return self.inner({**body, "model": self.to_id})


class EchoAs:
    """Rewrites the echo to a fixed ID: what a provider that does not
    report the serving model would look like to the caller."""

    def __init__(self, inner, echo: str):
        self.inner, self.echo = inner, echo

    def __call__(self, body):
        return {**self.inner(body), "model": self.echo}


# --- what Lakeshore's production parser did before April 8, 2026 --------

def lenient_reason(c: ModelContract, text: str) -> tuple[str, bool]:
    """Unknown codes become 'other'; bad JSON becomes ('other', True).
    It never raises, which is the problem: it never tells anyone."""
    obj = parse_json(text)
    if obj is None:
        return "other", True
    allowed = next(f.values for f in c.fields if f.name == "reason_code")
    code = obj.get("reason_code")
    return (code if code in allowed else "other",
            bool(obj.get("needs_person", True)))


def lenient_last_object(text: str) -> dict | None:
    """The parser that takes the last JSON object in a reply. It would
    have accepted every self-corrected desk note in the 2.1 run."""
    end = text.rfind("}")
    while end != -1:
        start = text.rfind("{", 0, end)
        while start != -1:
            try:
                obj = json.loads(text[start:end + 1])
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            start = text.rfind("{", 0, start)
        end = text.rfind("}", 0, end)
    return None
