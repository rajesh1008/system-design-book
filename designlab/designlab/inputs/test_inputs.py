"""Offline tests for the Chapter 23 input edge."""
from __future__ import annotations

import importlib.util
from dataclasses import replace
import os
import subprocess
import sys
import unittest
from pathlib import Path

from . import voice
from .contract import CONTRACTS
from .edge import (INTAKE_PATHS, Envelope, NotAdmitted, adapter, admit,
                   for_context, to_context_item)
from .pilot import run as pilot_run
from .route import population, sweep
from .samples import all_inputs, boarding_pass, letter, opening
from .web import NOTICE, notice_input, read

ROOT = Path(__file__).resolve().parent.parent


class TestContracts(unittest.TestCase):
    def test_no_contract_has_a_free_text_field(self):
        self.assertTrue(CONTRACTS)
        for c in CONTRACTS.values():
            self.assertFalse(c.free_text, c.name)

    def test_admit_keeps_only_contract_fields(self):
        for raw in all_inputs():
            env = admit(raw)
            names = {f.name for f in CONTRACTS[raw.contract].fields}
            self.assertLessEqual(set(env.fields), names)


class TestEdge(unittest.TestCase):
    def test_every_intake_path_tags_untrusted(self):
        raw = opening()[0]
        for path in INTAKE_PATHS:
            env = adapter(path)(replace(raw, channel=path))
            self.assertEqual(env.trust, "untrusted")
            self.assertEqual(len(env.provenance.sha256), 64)

    def test_assembler_refuses_raw_input(self):
        for bad in ("refund to card 7731", opening()[0], {"x": 1}):
            with self.assertRaises(NotAdmitted):
                for_context(bad)
        with self.assertRaises(ValueError):
            adapter("docs")(opening()[1])      # a voicemail on the docs path

    def test_hidden_footer_becomes_a_signal(self):
        env = admit(opening()[0])
        self.assertEqual(len(env.signals["hidden_text"]), 1)
        self.assertEqual(env.route, "review")
        self.assertNotIn("supersedes", for_context(env))

    def test_voice_date_mismatch_asks(self):
        env = admit(opening()[1])
        self.assertEqual(env.route, "ask")
        self.assertEqual(env.read_back, ["amount", "date"])

    def test_passport_misread_goes_to_review(self):
        env = admit(opening()[2])
        self.assertEqual(env.fields["number"].route, "review")

    def test_margin_note_never_reaches_context(self):
        env = admit(boarding_pass())
        self.assertNotIn("upgrade", for_context(env))
        self.assertGreaterEqual(len(env.signals["instruction_like"]), 1)


class TestLetter(unittest.TestCase):
    def test_contract_path_keeps_card_from_record(self):
        r = pilot_run(letter(), None)
        self.assertNotIn("7731", for_context(r["envelope"]))
        self.assertEqual(r["proposal"].card, "0952")
        self.assertEqual(r["refusals"], [])

    def test_injected_path_is_refused_at_gateway(self):
        r = pilot_run(letter(), "instruction-as-text")
        self.assertEqual(r["proposal"].card, "7731")
        self.assertEqual(len(r["refusals"]), 2)


class TestRouting(unittest.TestCase):
    def test_record_check_cuts_error_more_than_threshold(self):
        rows = {r["t"]: r for r in sweep(population())}
        self.assertGreater(rows[0.9]["err"], 0.04)
        self.assertLess(rows[0.9]["err_chk"], 0.001)
        self.assertGreater(rows[0.99]["review"], rows[0.9]["review"])


class TestVoice(unittest.TestCase):
    def test_streaming_meets_budget_batch_does_not(self):
        s = voice.summary(voice.simulate(streaming=True))
        b = voice.summary(voice.simulate(streaming=False))
        self.assertLess(s["p95"], voice.BUDGET_S)
        self.assertGreater(b["p95"], 6.0)

    def test_read_back_catches_mishearings(self):
        off = voice.read_back(enabled=False)
        on = voice.read_back(enabled=True)
        self.assertEqual(off["misheard"], on["misheard"])
        self.assertEqual(off["reached"], off["misheard"])
        self.assertLessEqual(on["reached"], 2)


class TestWeb(unittest.TestCase):
    def test_hidden_text_is_split_out(self):
        visible, hidden = read(NOTICE)
        self.assertEqual(len(hidden), 4)
        self.assertNotIn("voucher", visible)

    def test_fields_come_from_visible_text_only(self):
        env = admit(notice_input())
        text = for_context(env)
        for word in ("voucher", "Ignore", "desk@", "waive the fare"):
            self.assertNotIn(word, text)
        self.assertGreaterEqual(len(env.signals["instruction_like"]), 1)


@unittest.skipIf(importlib.util.find_spec("context") is None,
                 "context package not present")
class TestContextItem(unittest.TestCase):
    def test_envelope_becomes_task_slot_item(self):
        item = to_context_item(admit(letter()))
        self.assertEqual(item.slot, "task")
        self.assertNotIn("7731", item.text)


class TestDemo(unittest.TestCase):
    def test_every_part_runs_and_fits(self):
        from .demo import PARTS
        env = dict(os.environ, DESIGNLAB_OFFLINE="1")
        env.pop("ANTHROPIC_API_KEY", None)
        for part in PARTS:
            with self.subTest(part=part):
                r = subprocess.run([sys.executable, "-m", "inputs.demo",
                                    "--part", part], cwd=ROOT, env=env,
                                   capture_output=True, text=True,
                                   timeout=120)
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
                self.assertEqual([x for x in r.stdout.splitlines()
                                  if len(x) > 70], [])


if __name__ == "__main__":
    unittest.main()
