#!/usr/bin/env bash
# Chapter 37 lab: service objectives on outcomes, burn-rate alerts, the
# freeze rule, the two July incidents, time to stop, the game day,
# runbooks, and reviews. Offline. The live run replays the recorded
# golden-set answers; `python3 -m reliability.live` records anew
# (needs ANTHROPIC_API_KEY).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m reliability.demo --part objectives --uptime-only
echo
for part in objectives alerts budget storm; do
    "$PY" -m reliability.demo --part "$part"
    echo
done
"$PY" -m reliability.demo --part alerts --pinned
echo
"$PY" -m reliability.demo --part budget --extra 20
echo
for inc in july8 storm effect; do
    "$PY" -m reliability.demo --part stop --incident "$inc"
    echo
done
"$PY" -m reliability.demo --part stop --incident storm --tier3-first
echo
"$PY" -m reliability.demo --part stop --incident storm --tier2-only
echo
"$PY" -m reliability.demo --part gameday
echo
"$PY" -m reliability.demo --part gameday --fixed
echo
"$PY" -m reliability.demo --part runbook --old
echo
for part in runbook review card; do
    "$PY" -m reliability.demo --part "$part"
    echo
done
echo "== golden set, alias and dated snapshot, k=3 (recorded) =="
"$PY" -m reliability.live --replay
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest reliability.test_reliability \
    reliability.test_live -v
