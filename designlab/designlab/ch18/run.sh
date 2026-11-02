#!/usr/bin/env bash
# Chapter 18 lab: the cost model and budget enforcement. Cost per
# verified outcome from the recorded pilot tasks, the five levers, the
# caches, budgets held by the control plane, and a driver forecast.
# Offline; seed 18; no model call and no key. US dollars.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the cost lab, seed 18 =="
"$PY" -m cost.demo --seed 18
echo
echo "== failure injection: no step cap and no spend budget =="
"$PY" -m cost.demo --seed 18 --part budget --no-budget
echo
echo "== a semantic cache at a stricter threshold =="
"$PY" -m cost.demo --seed 18 --part semantic --threshold 0.95
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest cost.test_cost -v
