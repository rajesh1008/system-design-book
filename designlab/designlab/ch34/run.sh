#!/usr/bin/env bash
# Chapter 34 lab: evaluation as a release gate. Offline; no key needed.
# The live wording judge runs only with ANTHROPIC_API_KEY set.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== the Release Gate, June 2026, seed 34 =="
"$PY" -m evals.demo
echo
"$PY" -m evals.demo --part harvest --month april
echo
echo "== the live wording judge, replayed from fixtures =="
"$PY" -m evals.live --replay
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -W ignore::ResourceWarning -m unittest \
    evals.test_evals evals.test_live_evals -v
