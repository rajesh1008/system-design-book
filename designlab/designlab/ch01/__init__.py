"""designlab v0 (Chapter 1): one action end to end.

A model output becomes a proposal, a policy engine outside the loop
grants or denies a permission, an executor acts once under a key, a
reconciler that did not act verifies the effect, and every step writes
one line to a hash-linked trail. `checker.audit` reads the trail back
and counts what it can and cannot answer.

    python3 -m ch01.demo            # the lab, offline and seeded
    ./ch01/run.sh                   # the lab plus the tests
"""
from .v0 import (ACTOR, VERIFIER, Network, PolicyEngine, V0Loop,
                 classify_output, demo_shape)
from .checker import audit

__all__ = ["ACTOR", "VERIFIER", "Network", "PolicyEngine", "V0Loop",
           "classify_output", "demo_shape", "audit"]
