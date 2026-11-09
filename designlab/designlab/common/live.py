"""Skip logic for live tests.

Live tests are opt-in: they run only when RUN_LIVE=1 is set, the
environment holds ANTHROPIC_API_KEY, and DESIGNLAB_OFFLINE is not 1.
A key in the environment alone never starts a live call from a test.
This module reports whether the key is set; it never returns the value.
"""
from __future__ import annotations

import os
import unittest

KEY_ENV = "ANTHROPIC_API_KEY"
OFFLINE_ENV = "DESIGNLAB_OFFLINE"
RUN_LIVE_ENV = "RUN_LIVE"


def live_available() -> bool:
    """A key is set and the offline switch is off (explicit commands)."""
    if os.environ.get(OFFLINE_ENV) == "1":
        return False
    return bool(os.environ.get(KEY_ENV, "").strip())


def live_tests_enabled() -> bool:
    """Live tests also need the explicit opt-in RUN_LIVE=1."""
    return os.environ.get(RUN_LIVE_ENV) == "1" and live_available()


def skip_unless_live(obj):
    reason = (f"live test skipped: needs {RUN_LIVE_ENV}=1 and {KEY_ENV} "
              f"(and {OFFLINE_ENV} not 1)")
    return unittest.skipUnless(live_tests_enabled(), reason)(obj)
