#!/usr/bin/env bash
# Chapter 20 lab: the semantic layer, the query guard, entitlements,
# the itinerary graph, twelve recorded questions, and a replayed week.
# Offline; seed 20; the model answers replay from knowledge/fixtures.
# Set ANTHROPIC_API_KEY and run "python3 -m knowledge.live" to record.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export DESIGNLAB_OFFLINE=1

echo "== the lab, seed 20 =="
"$PY" -m knowledge.demo --seed 20
echo
echo "== the injected estimator outage =="
"$PY" -m knowledge.demo --seed 20 --part guard --inject no-estimate \
  || echo "(exit $?)"
echo
echo "== Try It Yourself =="
"$PY" -m knowledge.demo --seed 20 --part layer --add-metric
"$PY" -m knowledge.demo --seed 20 --part guard --no-row-limit
"$PY" -m knowledge.demo --seed 20 --part entitle --as-user talvarez
echo
echo "== tests =="
"$PY" -m unittest knowledge.test_knowledge -v
