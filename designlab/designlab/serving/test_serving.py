"""Chapter 14 tests: the serving lab. Offline; no model, no key."""
from __future__ import annotations

import contextlib
import io
import unittest

from common.text import too_long

from . import batching as bt
from . import demo
from . import speculative as sp
from .bakeoff import replay
from .cachekey import probe, response_key
from .disagg import best_split, colocated, erlang_c_wait
from .layout import LAYOUTS, lint
from .paged import fit
from .tco import break_even_calls, fleet, utilization
from .trace import Seg, day


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = day(14)

    def test_trace_matches_chapter_10_shape(self):
        calls = [c for t in self.tasks for c in t.calls]
        first = [LAYOUTS["stable-first"](t, t.calls[0]).tokens
                 for t in self.tasks]
        mean_in = sum(LAYOUTS["stable-first"](t, c).tokens
                      for t in self.tasks for c in t.calls) / len(calls)
        mean_out = sum(c.output for c in calls) / len(calls)
        self.assertAlmostEqual(sum(first) / len(first), 3400, delta=250)
        self.assertAlmostEqual(mean_in, 6217, delta=400)
        self.assertAlmostEqual(mean_out, 173, delta=15)

    def test_pilot_hit_is_nine_percent(self):
        r = replay(self.tasks, "pilot")
        self.assertEqual(round(r["hit"] * 100), 9)

    def test_stable_first_reaches_78(self):
        r = replay(self.tasks, "stable-first")
        self.assertEqual(round(r["hit"] * 100), 78)

    def test_cost_per_task_falls_by_more_than_half(self):
        a = replay(self.tasks, "pilot")["usd_per_task"]
        b = replay(self.tasks, "stable-first")["usd_per_task"]
        self.assertEqual(round((1 - b / a) * 100), 54)

    def test_clock_first_caches_nothing(self):
        self.assertEqual(replay(self.tasks, "clock-first")["hit"], 0.0)

    def test_lint_flags_dynamic_ahead_of_stable(self):
        t = self.tasks[0]
        for name in ("pilot", "clock-first"):
            self.assertTrue(lint(LAYOUTS[name](t, t.calls[1])), name)
        self.assertEqual(lint(LAYOUTS["stable-first"](t, t.calls[1])), [])

    def test_engines_agree_with_each_other(self):
        a = replay(self.tasks, "stable-first", "engine-a")["hit"]
        b = replay(self.tasks, "stable-first", "engine-b")["hit"]
        self.assertLess(abs(a - b), 0.01)


class TestIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = day(14)

    def test_salt_at_boundary_keeps_shared_hit(self):
        shared = replay(self.tasks, "stable-first", "engine-a", "shared")
        first = replay(self.tasks, "stable-first", "engine-a", "traveler")
        edge = replay(self.tasks, "stable-first", "engine-a", "boundary")
        self.assertAlmostEqual(edge["hit"], shared["hit"], places=6)
        self.assertLess(first["hit"], shared["hit"] - 0.03)

    def test_probe_leaks_only_without_salt(self):
        v = self.tasks[0]
        wrong = Seg("itin:guess", v.itinerary.tokens)
        self.assertTrue(probe(v, v.itinerary, "shared")["leak"])
        for mode in ("traveler", "boundary"):
            r, w = probe(v, v.itinerary, mode), probe(v, wrong, mode)
            self.assertFalse(r["leak"], mode)
            self.assertEqual(r["matched"], w["matched"], mode)

    def test_response_key_differs_by_tenant_and_policy(self):
        req = {"ask": "refund LTG-5172204"}
        base = ("trav-0001", "refunds-v3", "claude-opus-5-5", "sf@2")
        k = response_key(*base, req)
        self.assertNotEqual(k, response_key("trav-0002", *base[1:], req))
        self.assertNotEqual(k, response_key(base[0], "refunds-v4",
                                            *base[2:], req))
        self.assertEqual(k, response_key(*base, dict(req)))


class TestEngine(unittest.TestCase):
    def test_continuous_beats_static(self):
        s = bt.run("static", bt.workload(14))
        c = bt.run("continuous", bt.workload(14))
        self.assertGreater(c["tok_s"], 1.5 * s["tok_s"])
        self.assertLess(c["ttft_p95"], s["ttft_p95"] / 10)

    def test_chunked_prefill_lowers_itl(self):
        c = bt.run("continuous", bt.workload(14))
        k = bt.run("continuous", bt.workload(14), chunk=512)
        self.assertLess(k["itl_p95"], c["itl_p95"] / 3)

    def test_paged_fits_more_than_contiguous(self):
        ls = [6000 + 37 * i % 900 for i in range(400)]
        c, p, x = fit(ls, shared_prefix=2880)
        self.assertLess(c.requests, p.requests)
        self.assertLess(p.requests, x.requests)
        self.assertGreater(c.waste, 0.5)
        self.assertGreater(x.served_per_held, 1.0)

    def test_speculative_formula_matches_simulation(self):
        for a in (0.4, 0.7):
            self.assertAlmostEqual(sp.simulate(a, 4),
                                   sp.expected_tokens(a, 4), delta=0.03)

    def test_speculative_gain_shrinks_with_batch(self):
        self.assertGreater(sp.speedup(0.7, 4, 0.05, 1), 2.0)
        self.assertLess(sp.speedup(0.7, 4, 0.05, 128), 1.5)
        self.assertLess(sp.speedup(0.4, 4, 0.05, 64), 1.0)

    def test_split_helps_long_prompts(self):
        one = colocated(6.0, 12000, 250, 12)
        gp, two = best_split(6.0, 12000, 250, 12)
        self.assertLess(two.ttft_s, one.ttft_s)
        self.assertLess(two.itl_p95_s, one.itl_p95_s)

    def test_erlang_c_saturates(self):
        self.assertEqual(erlang_c_wait(2.0, 1.0, 2), float("inf"))
        self.assertGreater(erlang_c_wait(1.9, 1.0, 2),
                           erlang_c_wait(1.0, 1.0, 2))


class TestCost(unittest.TestCase):
    def test_break_even_and_utilization(self):
        f = fleet(2, 3.20)
        self.assertAlmostEqual(f.monthly, 2 * 3.20 * 730 + 8000)
        self.assertAlmostEqual(break_even_calls(f, 0.01), f.monthly / 0.01)
        self.assertLess(utilization(176679, 2, 1368, 173), 0.05)

    def test_idle_gpus_still_cost_staff(self):
        self.assertEqual(fleet(16, 0.0, sre_share=1.0).monthly, 16000.0)


class TestDemo(unittest.TestCase):
    def test_every_line_fits_the_page(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            for p in demo.PARTS:
                {"clocks": demo.part_clocks,
                 "batching": lambda: demo.part_batching(14, 64),
                 "paged": lambda: demo.part_paged(14),
                 "layout": lambda: demo.part_layout(14, "stable-first"),
                 "bakeoff": lambda: demo.part_bakeoff(14, "stable-first"),
                 "salt": lambda: demo.part_salt(14),
                 "probe": lambda: demo.part_probe(14),
                 "speculative": lambda: demo.part_speculative(0.4),
                 "disagg": demo.part_disagg,
                 "tco": lambda: demo.part_tco(14, 3.20),
                 "card": demo.part_card}[p]()
        self.assertEqual(too_long(buf.getvalue()), [])
        self.assertIn("78.43%", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
