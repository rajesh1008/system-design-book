#!/usr/bin/env bash
# Chapter 31 lab: policy engine, approval cards, temporal rules, effect
# budgets, signed bundles, and the three kill-switch tiers. Offline.
# The live run replays the recorded small-model answers;
# `python3 -m policy.live` records anew (needs ANTHROPIC_API_KEY).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in talked prompt tiers approval temporal budgets bundle \
            coverage; do
    "$PY" -m policy.demo --part "$part"
    echo
done
"$PY" -m policy.demo --part coverage --engine-down-at 30
echo
for tier in 1 2 3; do
    "$PY" -m policy.demo --part kill --tier "$tier"
    echo
done
"$PY" -m policy.demo --part kill --broken
echo
"$PY" -m policy.demo --part drill
echo
"$PY" -m policy.demo --part card
echo
echo "== small model, talked at as agent and as checker (recorded) =="
"$PY" -m policy.live --replay
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest policy.test_policy \
    policy.test_live -v
