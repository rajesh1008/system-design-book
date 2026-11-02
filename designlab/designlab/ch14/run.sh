#!/usr/bin/env bash
# Chapter 14 lab: inference serving. Three clocks, batching, paged
# memory, prompt layout and the prefix cache, cache salts, speculative
# decoding, disaggregation, and the self-host cost. Offline; seed 14;
# no model call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the serving lab, seed 14 =="
"$PY" -m serving.demo --seed 14
echo
echo "== the timestamp moved to the top =="
"$PY" -m serving.demo --seed 14 --part bakeoff --layout clock-first
"$PY" -m serving.demo --seed 14 --part layout --layout clock-first
echo
echo "== double the batch =="
"$PY" -m serving.demo --seed 14 --part batching --batch 128
echo
echo "== speculative acceptance at 40% =="
"$PY" -m serving.demo --part speculative --accept 0.4
echo
echo "== idle GPUs someone already paid for =="
"$PY" -m serving.demo --seed 14 --part tco --gpu-hour 0
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest serving.test_serving -v
