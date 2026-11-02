"""The model as a component: contracts, variance, and drift (Chapter 13).

A model call site is described by a contract (`contract.py`): what goes
in, what may come out, how it refuses, how slow and how dear it may be,
and which model version it is pinned to. The golden cases in `golden/`
are its contract tests, run live or from recorded fixtures (`runner.py`).
`variance.py` measures how much one input's output moves between runs,
and `drift.py` watches the contract tests over time and raises an alert
when the model behind a pin stops behaving like the one it was tested on.
"""
from .contract import (ModelContract, OutputField, Violation, check,
                       load_contract, load_contracts)

__all__ = ["ModelContract", "OutputField", "Violation", "check",
           "load_contract", "load_contracts"]
