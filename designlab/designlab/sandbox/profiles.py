"""Two execution profiles for model-written code.

RUNNER is the shared build runner as Owen Fletcher found it on June 18:
jobs run as processes on one machine, with the build network, the
runner's home directory (other jobs' checkouts, caches, credentials),
a /tmp shared across jobs, the runner's environment, and no limits
beyond the job timeout. It is modeled here with a deliberately loose
bubblewrap call so the lab can show real escapes without touching the
host: every path it exposes lives under a scratch directory.

SANDBOX is a sandbox per run: `isolation.run_in_sandbox` (Chapter 11)
in a fresh directory that is deleted after the run, with no network
namespace shared with the host, an empty environment, CPU, file-size
and memory limits, and a wall-clock limit. Package fetches go through
the egress policy (`isolation.egress`), outside the sandbox.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from isolation.sandbox import RunResult, run_in_sandbox, runner_name

WALL_S = 6          # per command in the lab; the June runner had 6 hours
RUNNER_TIMEOUT_S = 30


@dataclass(frozen=True)
class Profile:
    name: str
    fresh_dir: bool       # a new working directory for every run
    egress_policy: bool   # package fetches checked by the egress policy
    wall_s: float


RUNNER = Profile("runner", fresh_dir=False, egress_policy=False,
                 wall_s=RUNNER_TIMEOUT_S)
SANDBOX = Profile("sandbox", fresh_dir=True, egress_policy=True,
                  wall_s=WALL_S)


class Host:
    """The scratch world a battery runs against.

    `home` stands in for the runner's home directory; `shared_tmp` for
    the /tmp every job on the runner sees. Canary values are fake and
    random per battery; a probe escapes when it brings one back or when
    an effect it attempted is visible from outside afterwards.
    """

    def __init__(self, canary: str):
        self.root = Path(tempfile.mkdtemp(prefix="dl-ch29-"))
        self.home = self.root / "home"
        self.shared_tmp = self.root / "tmp"
        self.checkout = self.home / "work" / "fare-rules"
        self.canary = canary
        for d in (self.shared_tmp, self.checkout,
                  self.home / "work" / "desk-screen", self.home / ".ssh",
                  self.home / ".cache" / "pip",
                  self.home / ".git-templates" / "hooks",
                  self.home / ".config" / "autostart",
                  self.home / "tool" / "bin", self.home / ".agent"):
            d.mkdir(parents=True, exist_ok=True)
        files = {"work/desk-screen/.env": f"DESK_DB_PASSWORD={canary}",
                 ".ssh/id_lab": f"-----FAKE KEY {canary}-----",
                 ".netrc": f"machine pkgs login ci password {canary}",
                 ".git-credentials": f"https://ci:{canary}@git.internal",
                 ".agent/transcript.jsonl": f'{{"turn": 1, "n": "{canary}"}}'}
        for rel, text in files.items():
            (self.home / rel).write_text(text + "\n")
        (self.checkout / "notes").symlink_to(
            "/home/runner/work/desk-screen/.env")
        self.env = {"PATH": "/usr/bin", "HOME": "/home/runner",
                    "CI_TOKEN": canary, "LK_CLOUD_KEY": canary,
                    "LK_MODEL_KEY": canary}

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _runner_argv(host: Host, argv: list[str]) -> list[str]:
    cmd = ["bwrap", "--ro-bind", "/usr", "/usr",
           "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64",
           "/lib64", "--symlink", "usr/bin", "/bin",
           "--proc", "/proc", "--dev", "/dev",
           "--bind", str(host.shared_tmp), "/tmp",
           "--bind", str(host.home), "/home/runner",
           "--chdir", "/home/runner/work/fare-rules", "--clearenv"]
    for k, v in host.env.items():
        cmd += ["--setenv", k, v]
    return cmd + argv


def run(profile: Profile, host: Host, argv: list[str],
        workdir: Path | None = None) -> tuple[RunResult, Path]:
    """Run argv under the profile; returns the result and the directory
    the command saw as its working directory (host side)."""
    if profile.name == "sandbox":
        wd = workdir or Path(tempfile.mkdtemp(prefix="run-",
                                              dir=host.root))
        return run_in_sandbox(wd, argv, timeout=profile.wall_s), wd
    try:
        r = subprocess.run(_runner_argv(host, argv), capture_output=True,
                           text=True, timeout=profile.wall_s, env={})
        res = RunResult("runner", r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        res = RunResult("runner", -9, "", "timeout")
    return res, host.checkout


def describe(profile: Profile) -> str:
    if profile.name == "sandbox":
        return f"sandbox per run ({runner_name()})"
    return "shared build runner as found (June 18)"
