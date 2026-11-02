"""Chapter 29: code as the tool layer.

`battery` runs forty escape probes against an execution profile (the
shared build runner as found, or a sandbox per run built on
`isolation.run_in_sandbox`), `gate` is the merge service's review gate
for coding-agent proposals, `repo` runs a fixture repository's tests
inside the sandbox, and `browser` is a read-only computer-use reader
for a supplier portal with no API, simulated against an API call.
"""
from .battery import PROBES, BatteryResult, run_battery
from .gate import Approval, CIResult, GateVerdict, Proposal, review
from .profiles import RUNNER, SANDBOX, Profile, run

__all__ = ["PROBES", "BatteryResult", "run_battery", "Approval",
           "CIResult", "GateVerdict", "Proposal", "review", "RUNNER",
           "SANDBOX", "Profile", "run"]
