"""Tests for the Chapter 11 isolation lab. Offline; no key needed."""
from __future__ import annotations

import ast
import contextlib
import io
import json
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from common.text import too_long
from common.trail import check_trail

from .blast import (OutOfScope, ScopedKnowledge, blast_radius, build_world,
                    by_locator, design, probe_design, warm_pool)
from .egress import EgressPolicy, load_policy
from .sandbox import run_in_sandbox, runner_name
from .session import SessionStore, cross_read_suite


class TestSessions(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="iso-test-"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_one_private_dir_per_session(self):
        st = SessionStore(self.root)
        a, b = st.open("s-1", "LTG-1"), st.open("s-2", "LTG-2")
        self.assertNotEqual(a.workdir, b.workdir)
        self.assertEqual(stat.S_IMODE(a.workdir.stat().st_mode), 0o700)
        self.assertEqual(st.shared_writable(), [])

    def test_close_removes_the_dir(self):
        st = SessionStore(self.root)
        a = st.open("s-1", "LTG-1")
        a.upload("passport.jpg", b"scan:LTG-1")
        st.close(a)
        self.assertFalse(a.workdir.exists())

    def test_session_id_is_never_reused(self):
        st = SessionStore(self.root)
        st.open("s-1", "LTG-1")
        with self.assertRaises(FileExistsError):
            st.open("s-1", "LTG-9")

    def test_suite_finds_no_cross_reads(self):
        r = cross_read_suite(runs=1_000, seed=11)
        self.assertEqual(r.cross_reads, 0)
        self.assertEqual(r.leftovers, 0)
        self.assertTrue(r.ok)

    def test_injected_shared_dir_fails_the_suite(self):
        r = cross_read_suite(runs=1_000, seed=11, shared=True)
        self.assertGreater(r.cross_reads, 0)
        self.assertGreater(r.shared_paths_seen, 0)
        self.assertFalse(r.ok)


class TestSandbox(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="iso-sbx-"))
        self.store = SessionStore(self.root)
        self.me = self.store.open("s-1", "LTG-1")
        self.other = self.store.open("s-2", "LTG-2")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def runners(self):
        out = ["subprocess"]
        if runner_name() == "bwrap":
            out.append("auto")
        return out

    def test_tool_writes_inside_its_own_dir(self):
        for prefer in self.runners():
            with self.subTest(runner=prefer):
                r = run_in_sandbox(self.me.workdir, ["python3", "-c",
                                   "open('out.txt','w').write('ok')"],
                                   prefer=prefer)
                self.assertEqual(r.code, 0, r.stderr[-200:])
                self.assertEqual((self.me.workdir / "out.txt")
                                 .read_text(), "ok")

    def test_tool_cannot_write_into_another_session(self):
        target = self.other.workdir / "planted.txt"
        for prefer in self.runners():
            with self.subTest(runner=prefer):
                code = f"open({str(target)!r}, 'w').write('x')"
                r = run_in_sandbox(self.me.workdir, ["python3", "-c", code],
                                   prefer=prefer)
                self.assertNotEqual(r.code, 0)
                self.assertFalse(target.exists())

    def test_tool_cannot_open_a_socket(self):
        code = ("import socket\n"
                "socket.create_connection(('203.0.113.9', 443), 2)")
        for prefer in self.runners():
            with self.subTest(runner=prefer):
                r = run_in_sandbox(self.me.workdir, ["python3", "-c", code],
                                   prefer=prefer)
                self.assertNotEqual(r.code, 0)

    def test_environment_is_empty(self):
        code = "import os; print(sorted(os.environ))"
        for prefer in self.runners():
            with self.subTest(runner=prefer):
                r = run_in_sandbox(self.me.workdir, ["python3", "-c", code],
                                   prefer=prefer)
                self.assertNotIn("ANTHROPIC", r.stdout)
                self.assertLessEqual(len(ast.literal_eval(r.stdout)), 4)


class TestEgress(unittest.TestCase):
    def setUp(self):
        self.p = EgressPolicy()

    def test_eleven_hosts_with_an_owner(self):
        self.assertEqual(self.p.host_count(), 11)
        self.assertEqual(self.p.owner, "Owen Fletcher")
        for h in load_policy()["host"]:
            self.assertTrue(h["tools"] and h["reason"], h["name"])

    def test_listed_tool_and_host_allowed(self):
        v = self.p.check("refund", "https://gateway.lakeshore.internal/r")
        self.assertTrue(v.allowed)

    def test_host_is_normalized(self):
        v = self.p.check("refund", "https://GATEWAY.lakeshore.internal./r")
        self.assertTrue(v.allowed)

    def test_deny_by_default(self):
        cases = {"https://pypi.org/simple/": "host not listed",
                 "https://198.51.100.7/": "ip literal",
                 "http://169.254.169.254/latest/": "scheme http",
                 "https://gateway.lakeshore.internal:8443/": "host not "
                 "listed",
                 "https://gateway.lakeshore.internal@paste.example.net/":
                 "host not listed"}
        for url, why in cases.items():
            with self.subTest(url=url):
                v = self.p.check("refund", url)
                self.assertFalse(v.allowed)
                self.assertEqual(v.reason, why)

    def test_tool_must_be_listed_for_the_host(self):
        v = self.p.check("booking_read",
                         "https://gateway.lakeshore.internal/refund")
        self.assertFalse(v.allowed)
        self.assertEqual(v.reason, "tool not listed for host")

    def test_redirect_checked_hop_by_hop(self):
        v = self.p.follow("notice_read",
                          ["https://notices.lakeshore.internal/n/1",
                           "https://cdn.carrier.example/n/1"])
        self.assertFalse(v.allowed)
        self.assertEqual(v.host, "cdn.carrier.example")

    def test_every_denial_is_on_the_trail(self):
        self.p.check("code_run", "https://pypi.org/simple/", "s-9")
        self.p.check("doc_intake", "https://paste.example.net/", "s-9")
        lines = self.p.trail.lines
        self.assertEqual(len(lines), self.p.denied)
        self.assertEqual(json.loads(lines[0])["kind"], "egress_denied")
        self.assertEqual(check_trail(lines), [])


class TestBlast(unittest.TestCase):
    def setUp(self):
        self.w = build_world(11)
        self.me = self.w.itineraries[0]

    def radius(self, **kw) -> int:
        return blast_radius(probe_design(self.w, design(self.w, self.me,
                                                        **kw)))

    def test_isolated_session_reaches_one_itinerary(self):
        self.assertEqual(self.radius(), 1)

    def test_shared_dir_reaches_the_worker_shift(self):
        self.assertEqual(self.radius(shared_dir=True), 106)

    def test_shared_cache_reaches_every_cached_entry(self):
        self.assertEqual(self.radius(cache_key=by_locator), 240)

    def test_unscoped_knowledge_reaches_everything(self):
        self.assertEqual(self.radius(scoped=False), 2000)

    def test_scoped_view_refuses_other_itineraries(self):
        v = ScopedKnowledge(self.w.plane, self.me)
        v.context(self.me)
        with self.assertRaises(OutOfScope):
            v.context(self.w.itineraries[1])

    def test_littles_law_pool(self):
        in_use, pool = warm_pool(3.1, 31.0)
        self.assertAlmostEqual(in_use, 96.1, places=1)
        self.assertEqual(pool, 121)


class TestDemo(unittest.TestCase):
    def test_demo_lines_fit(self):
        from .demo import main
        for argv in (["--runs", "200"],
                     ["--runs", "200", "--inject", "shared-dir"],
                     ["--part", "blast", "--inject", "shared-cache"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main(argv), 0)
            self.assertEqual(too_long(buf.getvalue()), [])


if __name__ == "__main__":
    unittest.main()
