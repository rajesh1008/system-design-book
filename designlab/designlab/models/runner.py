"""Contract tests: run a contract's golden cases, live or from fixtures.

The same code runs both ways. Live, the client sends each case to the
pinned model and records the redacted request and response into
`models/fixtures/<contract>/`; offline, `FixtureTransport` replays those
recordings by request hash, so a test that passed live passes offline
for the same reason, and a change to the prompt, the pin, or max_tokens
finds no fixture and fails loudly.

`guarded_call` is the production path: check every call against the
contract, allow one repair attempt, and otherwise send the case to a
dead letter for a person. Tests measure first answers; production gets
one repair.
"""
from __future__ import annotations

import dataclasses
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

from common.client import ModelClient
from common.spend import SpendMeter
from common.trail import TrailWriter

from .contract import (ModelContract, Violation, check, check_input,
                       parse_json)

HERE = Path(__file__).parent
GOLDEN_DIR = HERE / "golden"
FIXTURE_DIR = HERE / "fixtures"


class TimedTransport:
    """Wraps a transport and records wall time into the response, so a
    replayed fixture carries the latency of the live call it came from."""

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, body: dict) -> dict:
        t0 = time.monotonic()
        resp = dict(self.inner(body))
        resp.setdefault("x_latency_ms",
                        round((time.monotonic() - t0) * 1000))
        return resp


def golden_cases(c: ModelContract) -> list[dict]:
    path = GOLDEN_DIR / c.golden
    return [json.loads(ln) for ln in path.read_text().splitlines() if ln]


class ContractClient(ModelClient):
    """The shared client, plus the provider's constrained decoding when
    the contract asks for it. The schema goes into the request body, so
    it is part of the request hash and of every recorded fixture."""

    schema: dict | None = None

    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        if self.schema is not None:
            body["output_config"] = {"format": {
                "type": "json_schema", "schema": self.schema}}
        return body


def client_for(c: ModelContract, transport, meter: SpendMeter,
               record_dir: Path | None = None) -> ModelClient:
    """A client whose request names the contract's model ID exactly,
    whether that ID is a pinned role in models.toml or an alias."""
    cl = ContractClient(c.role, meter=meter, transport=transport,
                        record_dir=record_dir)
    if c.decoding == "constrained":
        cl.schema = c.json_schema()
    if cl.pin.id != c.model_id:
        cl.pin = dataclasses.replace(cl.pin, id=c.model_id)
    return cl


@dataclass
class CaseResult:
    case_id: str
    echo: str
    violations: list[Violation]
    output: dict | None
    latency_s: float
    cost_usd: float
    raw: str | None = None

    @property
    def passed(self) -> bool:
        return not self.violations


@dataclass
class SuiteResult:
    contract: ModelContract
    cases: list[CaseResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(r.passed for r in self.cases)

    @property
    def echoes(self) -> set[str]:
        return {r.echo for r in self.cases}

    @property
    def p95_s(self) -> float:
        xs = sorted(r.latency_s for r in self.cases)
        return xs[max(0, math.ceil(0.95 * len(xs)) - 1)] if xs else 0.0

    @property
    def cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.cases)

    def suite_violations(self) -> list[Violation]:
        v = []
        if self.p95_s > self.contract.p95_latency_s:
            v.append(Violation("slow-p95", f"{self.p95_s:.1f} s"))
        return v

    def ok(self) -> bool:
        return (self.passed == len(self.cases)
                and not self.suite_violations())


def expectation(case: dict, obj: dict | None) -> list[Violation]:
    if obj is None:
        return []
    return [Violation("wrong-answer",
                      f"{k}={obj.get(k)!r}, want {want!r}")
            for k, want in case["expect"].items() if obj.get(k) != want]


class _Spy:
    """Keeps the last raw response so the runner can read its latency."""

    def __init__(self, inner):
        self.inner, self.last = inner, None

    def __call__(self, body):
        self.last = self.inner(body)
        return self.last


def run_suite(c: ModelContract, transport, meter: SpendMeter | None = None,
              record_dir: Path | None = None,
              trail: TrailWriter | None = None) -> SuiteResult:
    """First answers only: no repair, so a test sees what the model did."""
    meter = meter if meter is not None else SpendMeter(cap_usd=0.50)
    spy = _Spy(TimedTransport(transport))
    cl = client_for(c, spy, meter, record_dir)
    res = SuiteResult(c)
    for case in golden_cases(c):
        inputs = case["input"]
        bad_in = check_input(c, inputs)
        if bad_in:
            res.cases.append(CaseResult(case["id"], "", bad_in, None, 0, 0))
            continue
        comp = cl.complete(c.render(inputs), system=c.system,
                           max_tokens=c.max_tokens)
        latency = (spy.last or {}).get("x_latency_ms", 0) / 1000
        obj = parse_json(comp.text)
        v = check(c, comp, inputs) + expectation(case, obj)
        res.cases.append(CaseResult(case["id"], comp.model, v, obj,
                                    latency, comp.cost_usd, comp.text))
        if trail is not None:
            trail.append({"contract": c.name, "version": c.version,
                          "prompt": c.prompt_hash, "asked": c.model_id,
                          "echo": comp.model, "case": case["id"],
                          "pass": not v,
                          "violations": [x.code for x in v]})
    return res


@dataclass
class Guarded:
    outcome: str              # ok, repaired, dead-letter
    output: dict | None
    attempts: int
    violations: list[Violation]


def guarded_call(c: ModelContract, cl: ModelClient,
                 inputs: dict) -> Guarded:
    """The production path: contract check, one repair, then a person."""
    bad = check_input(c, inputs)
    if bad:
        return Guarded("dead-letter", None, 0, bad)
    prompt = c.render(inputs)
    comp = cl.complete(prompt, system=c.system, max_tokens=c.max_tokens)
    v = check(c, comp, inputs)
    if not v:
        return Guarded("ok", parse_json(comp.text), 1, [])
    if any(x.code in ("echo-drift", "refusal") for x in v):
        return Guarded("dead-letter", None, 1, v)
    repair = (prompt + "\nYour previous reply broke the output rules: "
              + "; ".join(str(x) for x in v)
              + ". Reply again with one JSON object that follows them.")
    comp2 = cl.complete(repair, system=c.system, max_tokens=c.max_tokens)
    v2 = check(c, comp2, inputs)
    if not v2:
        return Guarded("repaired", parse_json(comp2.text), 2, v)
    return Guarded("dead-letter", None, 2, v + v2)
