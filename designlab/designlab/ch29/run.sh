#!/usr/bin/env bash
# Chapter 29 lab: escape battery, review gate, read-only browser reader.
# Offline; needs bubblewrap for the battery. The live run replays the
# recorded small-model answers; `python3 -m sandbox.live` records anew.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== escape battery: sandbox per run =="
"$PY" -m sandbox.demo --part battery
echo
echo "== escape battery: the build runner as found =="
"$PY" -m sandbox.demo --part battery --profile runner
echo
echo "== try it: egress allows the booking replica =="
"$PY" -m sandbox.demo --part battery \
    --allow-host bookdb-ro.lakeshore.internal:5432
echo
echo "== review gate: eight proposals against fare-rules =="
"$PY" -m sandbox.demo --part gate
echo
echo "== computer use: read-only supplier portal reader =="
"$PY" -m sandbox.demo --part browser
echo
echo "== small model as the coding agent (recorded run) =="
"$PY" -m sandbox.live --replay
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest sandbox.test_sandbox \
    sandbox.test_live -v
