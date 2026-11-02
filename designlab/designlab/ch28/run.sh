#!/usr/bin/env bash
# Chapter 28 lab: the fare watch as an unattended loop. Offline; no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== the fare watch, June 12 to 28, seed 28 =="
"$PY" -m loops.demo
echo
echo "== try it: state in worker memory, restarted every six hours =="
"$PY" -m loops.demo --part state --state memory
echo
echo "== try it: the actor checks itself =="
"$PY" -m loops.demo --part verify --self-verify
echo
echo "== try it: a five-dollar loop day =="
"$PY" -m loops.demo --part budget --day-usd 5
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -W ignore::ResourceWarning -m unittest loops.test_loops -v
