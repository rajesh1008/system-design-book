#!/usr/bin/env bash
# Chapter 30 lab: the runtimes grid, the portability check, and the
# migration test. Offline; no live calls. The adapters replay
# synthetic fixtures shaped on two documented session models.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in grid inject features stale portable tie migrate skills; do
    echo "== $part =="
    "$PY" -m runtimes.demo --part "$part"
    echo
done
echo "== try it: weight portability twice =="
"$PY" -m runtimes.demo --part weight --weight prt=2
echo
echo "== try it: drop a runtime's memory switch =="
"$PY" -m runtimes.demo --part drop --drop agentcore:K1
echo
echo "== both extremes: AgentCore with every service =="
"$PY" -m runtimes.demo --part drop --drop agentcore:C1 \
    --drop agentcore:T2
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest runtimes.test_runtimes -v
"$PY" -m common.secretscan
