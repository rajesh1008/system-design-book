"""Offline unit tests for the shared utilities. No key, no network."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from common import client as cl
from common.clock import FixedClock
from common.ids import run_id
from common.live import KEY_ENV, OFFLINE_ENV, live_available
from common.models import pin, pins
from common.rand import derive_seed, seeded
from common.redact import (FIXTURE_BANNED, MASK, find_secrets, redact,
                           redact_text, scan_tree)
from common.spend import SpendCapExceeded, SpendMeter
from common.text import emit, too_long
from common.trail import GENESIS, TrailWriter, check_trail

FIXTURES = Path(__file__).with_name("fixtures")
# Built from parts so this file never holds a key-shaped string.
FAKE_KEY = "sk" + "-ant-" + "api03-" + "Zq" * 24


def fake_response(model="claude-haiku-5-5", text="ok", tin=10, tout=2):
    return {"model": model, "content": [{"type": "text", "text": text}],
            "stop_reason": "end_turn",
            "usage": {"input_tokens": tin, "output_tokens": tout}}


class Recorder:
    def __init__(self, resp=None):
        self.bodies, self.resp = [], resp or fake_response()

    def __call__(self, body):
        self.bodies.append(body)
        return self.resp


class TestClockIdsRand(unittest.TestCase):
    def test_fixed_clock_steps(self):
        c = FixedClock("2026-01-05T09:00:00+00:00", step_seconds=2)
        a, b = c.now(), c.now()
        self.assertEqual((b - a).total_seconds(), 2)

    def test_run_id_is_reproducible(self):
        def make():
            return run_id("run", FixedClock(), seeded(7, "x"))
        self.assertEqual(make(), make())
        self.assertRegex(make(), r"^run-20260105T090000-[0-9a-f]{6}$")

    def test_derived_seeds_differ_by_label(self):
        self.assertNotEqual(derive_seed(1, "a"), derive_seed(1, "b"))
        self.assertEqual(seeded(1, "a").random(), seeded(1, "a").random())


class TestModels(unittest.TestCase):
    def test_roles_are_pinned(self):
        self.assertEqual(set(pins()), {"small", "mid", "frontier", "dated"})
        self.assertEqual(pin("small").id, "claude-haiku-5-5")
        self.assertEqual(pin("claude-opus-5-5").role, "frontier")

    def test_unpinned_id_is_refused(self):
        with self.assertRaises(KeyError):
            pin("claude-latest")

    def test_prices_are_positive_and_ordered(self):
        for p in pins().values():
            self.assertGreater(p.output_usd_per_mtok, p.input_usd_per_mtok)
            self.assertLess(p.cache_read_usd_per_mtok, p.input_usd_per_mtok)


class TestRedact(unittest.TestCase):
    def test_masks_secret_fields_but_not_token_counts(self):
        out = redact({"api_key": "x", "authorization": "Bearer y",
                      "input_tokens": 5, "max_tokens": 8,
                      "nested": [{"password": "p"}]})
        self.assertEqual(out["api_key"], MASK)
        self.assertEqual(out["authorization"], MASK)
        self.assertEqual(out["nested"][0]["password"], MASK)
        self.assertEqual((out["input_tokens"], out["max_tokens"]), (5, 8))

    def test_masks_key_shapes_in_text(self):
        self.assertNotIn(FAKE_KEY, redact_text(f"key={FAKE_KEY} end"))
        self.assertTrue(find_secrets(f"oops {FAKE_KEY}"))

    def test_masks_the_env_value_whatever_its_shape(self):
        with mock.patch.dict(os.environ, {KEY_ENV: "plain-value-123456"}):
            self.assertEqual(redact_text("v=plain-value-123456"),
                             f"v={MASK}")

    def test_fixture_rules_are_stricter(self):
        word = FIXTURE_BANNED[0]
        self.assertFalse(find_secrets(f"header {word}"))
        self.assertTrue(find_secrets(f"header {word}", fixture=True))

    def test_scan_tree_flags_a_planted_key(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "fixtures").mkdir()
            (Path(d) / "fixtures" / "a.json").write_text(FIXTURE_BANNED[1])
            (Path(d) / "b.py").write_text(f"K = '{FAKE_KEY}'")
            self.assertEqual(len(scan_tree(Path(d))), 2)

    def test_committed_tree_is_clean(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(scan_tree(root), {})


class TestSpend(unittest.TestCase):
    def test_price_arithmetic(self):
        p = pin("mid")   # $2 in, $10 out per million
        self.assertAlmostEqual(SpendMeter.price(p, 1_000_000, 100_000), 3.0)

    def test_cap_refuses_before_the_call(self):
        meter = SpendMeter(cap_usd=0.0001)
        t = Recorder()
        c = cl.ModelClient("frontier", meter=meter, transport=t)
        with self.assertRaises(SpendCapExceeded):
            c.complete("x" * 4000, max_tokens=1000)
        self.assertEqual(t.bodies, [])

    def test_ledger_written(self):
        with tempfile.TemporaryDirectory() as d:
            m = SpendMeter(ledger_path=Path(d) / "ledger.jsonl")
            m.record(pin("small"), {"input_tokens": 10, "output_tokens": 2})
            rows = (Path(d) / "ledger.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(rows[0])["model"], "claude-haiku-5-5")


class TestTrail(unittest.TestCase):
    def setUp(self):
        self.t = TrailWriter(clock=FixedClock())
        for i in range(4):
            self.t.append({"event": "e", "i": i, "token": "t"})

    def test_chain_checks_and_redacts(self):
        self.assertEqual(check_trail(self.t.lines), [])
        first = json.loads(self.t.lines[0])
        self.assertEqual((first["prev"], first["token"]), (GENESIS, MASK))

    def test_edit_delete_and_reorder_are_caught(self):
        edited = list(self.t.lines)
        edited[1] = edited[1].replace('"i": 1', '"i": 9')
        self.assertTrue(check_trail(edited))
        self.assertTrue(check_trail(self.t.lines[:1] + self.t.lines[2:]))
        swapped = [self.t.lines[1], self.t.lines[0]] + self.t.lines[2:]
        self.assertTrue(check_trail(swapped))

    def test_file_backed(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "trail.jsonl"
            w = TrailWriter(path, clock=FixedClock())
            w.append({"event": "a"})
            w.append({"event": "b"})
            lines = path.read_text().splitlines()
            self.assertEqual(check_trail(lines), [])


class TestText(unittest.TestCase):
    def test_emit_refuses_long_lines(self):
        with self.assertRaises(ValueError):
            emit("x" * 71)
        self.assertEqual(too_long("ok\n" + "y" * 80), ["y" * 80])


class TestClient(unittest.TestCase):
    def test_body_shape_and_completion(self):
        t = Recorder()
        c = cl.ModelClient("small", meter=SpendMeter(), transport=t)
        r = c.complete("hi", system="be brief", max_tokens=8)
        body = t.bodies[0]
        self.assertEqual(body["model"], "claude-haiku-5-5")
        self.assertEqual(body["system"], "be brief")
        self.assertNotIn("temperature", body)
        self.assertEqual((r.text, r.drifted, r.cached), ("ok", False, False))
        self.assertGreater(r.cost_usd, 0)

    def test_drift_is_visible(self):
        t = Recorder(fake_response(model="claude-haiku-9"))
        r = cl.ModelClient("small", transport=t).complete("hi")
        self.assertTrue(r.drifted)

    def test_cache_hit_skips_transport_and_meter(self):
        with tempfile.TemporaryDirectory() as d:
            t, m = Recorder(), SpendMeter()
            c = cl.ModelClient("small", meter=m, transport=t, cache_dir=d)
            c.complete("hi")
            r = c.complete("hi")
            self.assertEqual((len(t.bodies), m.calls, r.cached),
                             (1, 1, True))

    def test_missing_key_raises_without_network(self):
        env = {k: v for k, v in os.environ.items() if k != KEY_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            c = cl.ModelClient("small")
            with self.assertRaises(cl.MissingKey):
                c.complete("hi")
            self.assertEqual(c.transport.calls, 0)
            self.assertFalse(live_available())

    def test_offline_switch_disables_live(self):
        with mock.patch.dict(os.environ, {KEY_ENV: "v", OFFLINE_ENV: "1"}):
            self.assertFalse(live_available())

    def test_key_alone_never_enables_live_tests(self):
        from common.live import live_tests_enabled
        env = {k: v for k, v in os.environ.items()
               if k not in ("RUN_LIVE", OFFLINE_ENV)}
        env[KEY_ENV] = "v"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(live_tests_enabled())
        env["RUN_LIVE"] = "1"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(live_tests_enabled())

    def test_key_never_reaches_repr_errors_or_records(self):
        with mock.patch.dict(os.environ, {KEY_ENV: FAKE_KEY}):
            def leaky(body):
                raise cl.APIError(401, f"bad key {FAKE_KEY}")
            c = cl.ModelClient("small", transport=leaky)
            with self.assertRaises(cl.APIError) as ctx:
                c.complete("hi")
            self.assertNotIn(FAKE_KEY, str(ctx.exception))
            self.assertNotIn(FAKE_KEY, repr(c) + repr(cl.HttpTransport()))
            with tempfile.TemporaryDirectory() as d:
                resp = fake_response(text=f"echo {FAKE_KEY}")
                cl.ModelClient("small", transport=Recorder(resp),
                               record_dir=d).complete("hi")
                saved = "".join(p.read_text() for p in Path(d).iterdir())
                self.assertNotIn(FAKE_KEY, saved)
                self.assertEqual(find_secrets(saved, fixture=True), [])

    def test_committed_fixture_replays(self):
        c = cl.ModelClient("small", transport=cl.FixtureTransport(FIXTURES))
        r = c.complete("Reply with the word ok.", max_tokens=8)
        self.assertEqual(r.text.strip().lower().rstrip("."), "ok")
        self.assertFalse(r.drifted)
        with self.assertRaises(cl.NoFixture):
            c.complete("something never recorded", max_tokens=8)


if __name__ == "__main__":
    unittest.main()
