"""designlab.common: shared utilities every module builds on (Batch 0).

Run ids, a clock, seeded randomness, the trail writer and checker,
redaction, the spend meter, pinned model IDs, the live-test skip logic,
and the model client. Standard library only.
"""
from .clock import Clock, FixedClock, SystemClock
from .ids import run_id
from .rand import derive_seed, seeded
from .redact import redact, find_secrets
from .spend import SpendCapExceeded, SpendMeter
from .trail import TrailWriter, check_trail
from .models import ModelPin, pin, pins
from .client import (APIError, Completion, FixtureTransport, MissingKey,
                     ModelClient)

__all__ = ["Clock", "FixedClock", "SystemClock", "run_id", "derive_seed",
           "seeded", "redact", "find_secrets", "SpendCapExceeded",
           "SpendMeter", "TrailWriter", "check_trail", "ModelPin", "pin",
           "pins", "APIError", "Completion", "FixtureTransport",
           "MissingKey", "ModelClient"]
