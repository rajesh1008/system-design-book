#!/usr/bin/env bash
# Chapter 11 lab: session isolation, the sandbox runner, egress policy,
# and blast radius. Offline; seed 11; no model call and no key needed.
# Uses bubblewrap when it is installed, else a restricted subprocess.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== isolation as designed =="
"$PY" -m isolation.demo --seed 11
echo
echo "== injected: two sessions share one working directory =="
"$PY" -m isolation.demo --seed 11 --inject shared-dir --part suite
"$PY" -m isolation.demo --seed 11 --inject shared-dir --part blast
echo
echo "== injected: a summary cache keyed without the tenant =="
"$PY" -m isolation.demo --seed 11 --inject shared-cache --part blast
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest isolation.test_isolation -v
