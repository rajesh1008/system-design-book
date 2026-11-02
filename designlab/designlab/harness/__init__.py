"""Chapter 25: the harness as a versioned artifact.

The loop, its tools, its context policy, its Stop Conditions and its
Budgets are declared in one Harness Manifest (`manifests/*.toml`). The
manifest is resolved (tool descriptions included), hashed, registered
before it may deploy, and its short hash is written into every trail
line. `loops` runs a refund case two ways, as free-form ReAct and as an
explicit state machine; `suite` is the harness test suite.
"""
