#!/usr/bin/env bash
# Chapter 17 lab: the decision tree, distillation with a time split,
# cost per step, preference pairs, and verifiable rewards. Offline;
# seed 17; the teacher labels replay from adapt/fixtures. Set
# ANTHROPIC_API_KEY and run "python3 -m adapt.live" to record them anew.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export DESIGNLAB_OFFLINE=1

echo "== the lab, seed 17 =="
"$PY" -m adapt.demo --seed 17
echo
echo "== the injected random split =="
"$PY" -m adapt.demo --seed 17 --inject random || echo "(exit $?)"
echo
echo "== Try It Yourself =="
"$PY" -m adapt.demo --seed 17 --part distill --tuned
"$PY" -m adapt.demo --seed 17 --part distill --half
"$PY" -m adapt.demo --seed 17 --part distill --new-type
echo
echo "== tests =="
"$PY" -m unittest adapt.test_adapt -v
