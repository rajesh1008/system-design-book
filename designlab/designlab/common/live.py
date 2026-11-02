"""Skip logic for live tests.

Live tests run only when ANTHROPIC_API_KEY is set in the environment.
This module reports whether it is set; it never returns the value.
"""
from __future__ import annotations

import os
import unittest

KEY_ENV = "ANTHROPIC_API_KEY"
OFFLINE_ENV = "DESIGNLAB_OFFLINE"


def live_available() -> bool:
    if os.environ.get(OFFLINE_ENV) == "1":
        return False
    return bool(os.environ.get(KEY_ENV, "").strip())


def skip_unless_live(obj):
    reason = f"{KEY_ENV} not set (or {OFFLINE_ENV}=1); live test skipped"
    return unittest.skipUnless(live_available(), reason)(obj)
