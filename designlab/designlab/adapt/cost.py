"""Cost of one classification step, before and after distillation.

Prices come from common/models.toml. The step's production prompt is
the case packet plus the label definitions: about 1,200 input tokens
and 12 output tokens. After distillation a step costs the student's
serving share, plus the escalations that still go to the frontier,
plus the month's upkeep (fresh teacher labels and the golden-set run)
spread over the month's steps.
"""
from __future__ import annotations

from dataclasses import dataclass

from common.models import pin
from common.spend import SpendMeter

STEP_IN = 1200
STEP_OUT = 12
# Student serving: a shared GPU at about $1.80 an hour classifies about
# 25 steps a second, so about $0.00002 a step.
SERVE_USD = 0.00002
GA_STEPS = 175_000           # a month at 2.1 million changes a year
PILOT_STEPS = 31_500         # May 2026: 18% of changes reach the agent


def frontier_step(role: str = "frontier") -> float:
    return SpendMeter.price(pin(role), STEP_IN, STEP_OUT)


@dataclass
class StepCost:
    frontier: float
    serve: float
    escalate: float
    upkeep: float

    @property
    def student(self) -> float:
        return self.serve + self.escalate + self.upkeep

    @property
    def ratio(self) -> float:
        return self.frontier / self.student


def distilled(escalation: float, steps_per_month: int,
              new_labels: int = 600, golden: int = 1200) -> StepCost:
    f = frontier_step()
    upkeep = (new_labels + golden) * f / steps_per_month
    return StepCost(f, SERVE_USD, escalation * f, upkeep)
