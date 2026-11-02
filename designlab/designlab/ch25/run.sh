#!/usr/bin/env bash
# Chapter 25: the agent loop and the harness as a versioned artifact.
# Offline. The live smoke is separate: python3 -m harness.live needs
# ANTHROPIC_API_KEY in the environment and costs well under one cent.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the manifest for harness v1 =="
"$PY" -m harness.demo --case manifest
echo
echo "== May 27 and May 28: one settings edit, no version =="
"$PY" -m harness.demo --case may28
echo
echo "== the deploy check =="
"$PY" -m harness.demo --case deploy
echo
echo "== a reworded tool description =="
"$PY" -m harness.demo --case description
echo
echo "== two loop shapes, 1,000 refund cases =="
"$PY" -m harness.demo --case shapes
echo
echo "== the harness suite on the first test build =="
"$PY" -m harness.demo --case suite --manifest servicing-1.0.0-rc1
echo
echo "== the harness suite on 1.1.0 =="
"$PY" -m harness.demo --case suite --manifest servicing-1.1.0
echo
echo "== one refund, traced =="
"$PY" -m harness.demo --case trail
echo
echo "== the live smoke, replayed from its fixtures =="
"$PY" -m harness.live --replay
echo
echo "== offline tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest harness.test_harness -v
echo
echo "== the deploy test under inject (expected to fail) =="
HARNESS_INJECT=settings DESIGNLAB_OFFLINE=1 \
  "$PY" -m unittest harness.test_harness.TestDeploy \
  || echo "expected: the settings-file edit is not a registered release"
