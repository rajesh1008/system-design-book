"""Replay test for the Chapter 23 image extraction (offline)."""
from __future__ import annotations

import unittest

from common.redact import find_secrets

from .vision import FIELDS, FIXTURES, IMAGE, extract


class ReplayVision(unittest.TestCase):
    def test_recorded_read_has_fields_and_flag_only(self):
        out, comp, _ = extract(record=False)
        self.assertEqual(set(out), {"fields", "confidence",
                                    "instruction_like"})
        self.assertEqual(set(out["fields"]), set(FIELDS))
        self.assertEqual(out["fields"]["locator"], "HN8C2V")
        self.assertIs(out["instruction_like"], True)
        self.assertNotIn("business", str(out["fields"]))

    def test_image_is_committed_and_fixture_is_clean(self):
        self.assertTrue(IMAGE.read_bytes().startswith(b"\x89PNG"))
        for p in FIXTURES.glob("*.json"):
            text = p.read_text()
            self.assertNotIn("iVBOR", text)      # no image bytes stored
            self.assertEqual(find_secrets(text, fixture=True), [])
