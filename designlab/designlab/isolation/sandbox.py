"""Run a tool's command inside the session's sandbox.

With bubblewrap (`bwrap`) on the path, the command gets a read-only
/usr, a private /tmp, its own session directory bound at /work, no
network namespace shared with the host, an empty environment, and dies
with its parent. Without bubblewrap, the fallback is a restricted
subprocess: working directory set to the session, an empty environment,
CPU, file-size, and address-space limits, and (for Python tools) an
audit hook that refuses writes outside /work-equivalent paths and
refuses every socket connect. The fallback is weaker, and `runner_name`
says which one ran so the trail can record it.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

LIMITS = {"cpu_s": 5, "file_mb": 16, "mem_mb": 512}

GUARD = r'''
import os, sys
_root = os.path.realpath(os.getcwd())
def _hook(event, args):
    if event == "open":
        path, mode = args[0], args[1]
        if isinstance(path, int):
            return
        w = isinstance(mode, str) and any(c in mode for c in "wax+")
        w = w or (isinstance(args[2], int) and args[2] & 0o3)
        real = os.path.realpath(path)
        if w and not real.startswith(_root + os.sep) and real != _root:
            raise PermissionError("outside session dir")
    elif event in ("socket.connect", "socket.bind"):
        raise PermissionError("network refused")
    elif event in ("os.remove", "os.rename", "os.mkdir", "os.rmdir"):
        real = os.path.realpath(str(args[0]))
        if not real.startswith(_root + os.sep):
            raise PermissionError("outside session dir")
sys.addaudithook(_hook)
'''


@dataclass
class RunResult:
    runner: str
    code: int
    stdout: str
    stderr: str


def runner_name(prefer: str = "auto") -> str:
    if prefer == "subprocess":
        return "subprocess"
    if shutil.which("bwrap") and _bwrap_works():
        return "bwrap"
    return "subprocess"


_BWRAP_OK: bool | None = None


def _bwrap_works() -> bool:
    global _BWRAP_OK
    if _BWRAP_OK is None:
        try:
            r = subprocess.run(_bwrap_argv(Path("/tmp"), ["/bin/true"]),
                               capture_output=True, timeout=10)
            _BWRAP_OK = r.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            _BWRAP_OK = False
    return _BWRAP_OK


def _bwrap_argv(workdir: Path, argv: list[str]) -> list[str]:
    base = ["bwrap", "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64",
            "/lib64", "--symlink", "usr/bin", "/bin",
            "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
            "--bind", str(workdir), "/work", "--chdir", "/work",
            "--unshare-all", "--die-with-parent", "--new-session",
            "--clearenv", "--setenv", "PATH", "/usr/bin",
            "--setenv", "HOME", "/work"]
    return base + argv


def _limits() -> None:   # runs in the child before exec
    import resource
    resource.setrlimit(resource.RLIMIT_CPU, (LIMITS["cpu_s"],) * 2)
    mb = 1024 * 1024
    resource.setrlimit(resource.RLIMIT_FSIZE, (LIMITS["file_mb"] * mb,) * 2)
    resource.setrlimit(resource.RLIMIT_AS, (LIMITS["mem_mb"] * mb,) * 2)


def run_in_sandbox(workdir: Path, argv: list[str], timeout: float = 20,
                   prefer: str = "auto") -> RunResult:
    """Run argv with the session directory as the only writable place.

    A Python tool is passed as ["python3", "-c", code]; under the
    fallback the guard is prepended to the code.
    """
    workdir = Path(workdir).resolve()
    name = runner_name(prefer)
    if name == "bwrap":
        cmd = _bwrap_argv(workdir, argv)
        env = {}
        pre = _limits
    else:
        cmd = list(argv)
        if cmd[:2] == ["python3", "-c"]:
            cmd = [sys.executable, "-I", "-c", GUARD + "\n" + cmd[2]]
        env = {"PATH": "/usr/bin", "HOME": str(workdir)}
        pre = _limits
    try:
        r = subprocess.run(cmd, cwd=workdir, env=env, capture_output=True,
                           text=True, timeout=timeout, preexec_fn=pre)
        return RunResult(name, r.returncode, r.stdout, r.stderr)
    except subprocess.TimeoutExpired:
        return RunResult(name, -9, "", "timeout")
