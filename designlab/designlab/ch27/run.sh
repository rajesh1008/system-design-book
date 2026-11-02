#!/usr/bin/env bash
# Chapter 27 lab: one agent against orchestrator-worker on the golden
# set, routing by legs, the talking stick across workers, the relay
# baton, hierarchy depth, voting and debate, and the topology card.
# Offline; seed 27. The live sample replays from
# topology/fixtures/live; set ANTHROPIC_API_KEY and run
# "python3 -m topology.live --record" to record it anew.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
export DESIGNLAB_OFFLINE=1

echo "== the lab, seed 27 =="
"$PY" -m topology.demo --seed 27
echo
echo "== the injected June 16 design =="
"$PY" -m topology.demo --seed 27 --inject shared || echo "(exit $?)"
echo
echo "== the live sample, replayed =="
"$PY" -m topology.live
echo
echo "== Try It Yourself =="
"$PY" -m topology.demo --seed 27 --part compare --third-worker
"$PY" -m topology.demo --seed 27 --part compare --brief-tokens 600
"$PY" -m topology.demo --seed 27 --part compare --call-cap 40
"$PY" -m topology.demo --seed 27 --part vote --rho 0
echo
echo "== tests =="
"$PY" -m unittest topology.test_topology topology.test_live_topology -v
