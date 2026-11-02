"""Live tests against the provider. They skip cleanly without a key.

Six HTTP calls per run: one per pinned role, one cache check, and one
deliberately invalid model ID (rejected, so not billed). Every prompt is
six words and every reply is capped at eight tokens.
"""
from __future__ import annotations

import dataclasses
import os
import tempfile
import unittest
from pathlib import Path

from common import client as cl
from common.live import KEY_ENV, skip_unless_live
from common.models import pins
from common.redact import find_secrets
from common.spend import SpendMeter

PROMPT = "Reply with the word ok."
METER = SpendMeter(cap_usd=0.05)


@skip_unless_live
class TestLivePins(unittest.TestCase):
    def check_role(self, role):
        with tempfile.TemporaryDirectory() as d:
            c = cl.ModelClient(role, meter=METER, record_dir=d)
            r = c.complete(PROMPT, max_tokens=8)
            self.assertEqual(r.model, c.pin.id, "pinned ID drifted")
            self.assertIn("ok", r.text.lower())
            self.assertLessEqual(r.output_tokens, 8)
            self.assertGreater(r.cost_usd, 0)
            saved = "".join(p.read_text() for p in Path(d).iterdir())
            self.assertEqual(find_secrets(saved, fixture=True), [])
            self.assertNotIn(os.environ[KEY_ENV], saved)

    def test_small(self):
        self.check_role("small")

    def test_mid(self):
        self.check_role("mid")

    def test_frontier(self):
        self.check_role("frontier")

    def test_dated(self):
        self.check_role("dated")

    def test_all_roles_covered(self):
        names = {n[5:] for n in dir(self) if n.startswith("test_")}
        self.assertLessEqual(set(pins()), names)


@skip_unless_live
class TestLiveClient(unittest.TestCase):
    def test_cache_repeat_makes_no_second_call(self):
        with tempfile.TemporaryDirectory() as d:
            t = cl.HttpTransport()
            c = cl.ModelClient("small", meter=METER, transport=t,
                               cache_dir=d)
            first = c.complete("Reply with the word yes.", max_tokens=8)
            again = c.complete("Reply with the word yes.", max_tokens=8)
            self.assertEqual(t.calls, 1)
            self.assertEqual((first.cached, again.cached), (False, True))
            self.assertEqual(first.text, again.text)

    def test_unknown_model_error_is_clean(self):
        c = cl.ModelClient("small", meter=METER)
        c.pin = dataclasses.replace(c.pin, id="claude-not-a-model-0")
        with self.assertRaises(cl.APIError) as ctx:
            c.complete(PROMPT, max_tokens=8)
        self.assertIn(ctx.exception.status, (400, 404))
        self.assertNotIn(os.environ[KEY_ENV], str(ctx.exception))



def tearDownModule():
    if METER.calls:
        print(f"\nlive spend: billed calls={METER.calls} "
              f"usd={METER.spent_usd:.6f}")


if __name__ == "__main__":
    unittest.main()
