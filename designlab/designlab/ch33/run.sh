#!/usr/bin/env bash
# Chapter 33 lab: the injection and poisoning battery. Offline. The
# live run replays the recorded small-model answers; `python3 -m
# threats.live` records anew (about half a cent).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== battery: 61 attacks, obedient model =="
"$PY" -m threats.demo --part battery
echo
echo "== what stopped each attack =="
"$PY" -m threats.demo --part stops
echo
echo "== the proposals policy refused =="
"$PY" -m threats.demo --part proposals
echo
echo "== one attack, traced: a poisoned fare rule =="
"$PY" -m threats.demo --part trace --attack T01
echo
echo "== the three legs, from configuration =="
"$PY" -m threats.demo --part trifecta
echo
echo "== try it: no session binding =="
"$PY" -m threats.demo --part battery --no-session
echo
echo "== small model in place of the obedient one (recorded run) =="
"$PY" -m threats.live --replay
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest threats.test_threats \
    threats.test_live -v
