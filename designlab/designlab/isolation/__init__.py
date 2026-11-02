"""Chapter 11: tenancy, isolation, and sandboxes for agent sessions.

One working directory per session with no shared writable path, a
sandbox runner (bubblewrap when present, else a restricted subprocess),
an egress allow-list by tool with denials written to the trail, and a
blast-radius calculator that probes what one session can reach.
Offline, seeded, standard library only.
"""
from .blast import Resource, blast_radius, probe_design
from .egress import EgressPolicy, Verdict, load_policy
from .sandbox import RunResult, run_in_sandbox, runner_name
from .session import Session, SessionStore, SuiteResult, cross_read_suite

__all__ = ["Resource", "blast_radius", "probe_design", "EgressPolicy",
           "Verdict", "load_policy", "RunResult", "run_in_sandbox",
           "runner_name", "Session", "SessionStore", "SuiteResult",
           "cross_read_suite"]
