"""Reasoning budgets: test-time compute as a routing lever.

A candidate for a step is a model and a reasoning budget. The budget is
part of the request body, so it is part of the request hash, the
recorded fixture, and the trail; a step cannot think longer without the
record showing it.

As of November 2, 2026, the provider's current models take the budget
as an effort level in `output_config` (low, medium, high, xhigh, max);
the older form, `thinking` with a token count, is refused with HTTP 400
on these models. "default" sends neither and leaves the provider's
adaptive behavior in place. The output tokens a model spends thinking
are billed as output, so the meter prices them like any other.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from common.models import pin

from models.contract import ModelContract
from models.runner import ContractClient, client_for

EFFORTS = ("default", "low", "medium", "high", "xhigh", "max")
TIERS = ("small", "mid", "frontier")


class BudgetRefused(ValueError):
    """A route asked for more reasoning than the control plane allows."""


@dataclass(frozen=True)
class Candidate:
    role: str
    effort: str = "default"

    @classmethod
    def parse(cls, text: str) -> "Candidate":
        role, _, effort = text.partition("@")
        c = cls(role, effort or "default")
        if c.role not in TIERS or c.effort not in EFFORTS:
            raise ValueError(f"bad candidate {text!r}")
        return c

    @property
    def label(self) -> str:
        return self.role if self.effort == "default" \
            else f"{self.role}@{self.effort}"

    @property
    def tier(self) -> int:
        return TIERS.index(self.role)


def cap(c: Candidate, max_effort: str) -> Candidate:
    """The control plane's ceiling. A route above it is refused, not
    quietly lowered, so the table and the trail never disagree."""
    if EFFORTS.index(c.effort) > EFFORTS.index(max_effort):
        raise BudgetRefused(f"{c.label} exceeds the cap {max_effort}")
    return c


class BudgetClient(ContractClient):
    effort: str = "default"

    def request_body(self, prompt, system, max_tokens, temperature):
        body = super().request_body(prompt, system, max_tokens,
                                    temperature)
        if self.effort != "default":
            cfg = dict(body.get("output_config", {}))
            cfg["effort"] = self.effort
            body["output_config"] = cfg
        return body


def contract_for(c: ModelContract, cand: Candidate) -> ModelContract:
    """The same step's contract, pinned to the candidate's model. The
    step's limits (latency, cost, inputs, output) stay the step's."""
    if c.role == cand.role:
        return c
    p = pin(cand.role)
    return dataclasses.replace(c, role=cand.role, model_id=p.id,
                               expect_echo=p.id)


def client(c: ModelContract, cand: Candidate, transport, meter,
           record_dir=None) -> BudgetClient:
    base = client_for(c, transport, meter, record_dir)
    cl = BudgetClient(c.role, meter=meter, transport=transport,
                      record_dir=record_dir)
    cl.pin, cl.schema, cl.effort = base.pin, base.schema, cand.effort
    return cl
