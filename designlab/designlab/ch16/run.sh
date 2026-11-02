#!/usr/bin/env bash
# Chapter 16: the tool-argument validation layer.
# Offline. The live lab is separate: python3 -m toolargs.live needs
# ANTHROPIC_API_KEY in the environment and costs about one US cent.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the two effect tools as the API receives them =="
"$PY" -m toolargs.demo --case tools
echo
echo "== the opening call, check by check =="
"$PY" -m toolargs.demo --case okafor
echo
echo "== what the model is sent back for it =="
"$PY" -m toolargs.demo --case verdict
echo
echo "== schema and world validation, repair budget 2 =="
"$PY" -m toolargs.demo --seed 16
echo
echo "== inject: schema-only (world validation off) =="
"$PY" -m toolargs.demo --seed 16 --inject schema-only
echo
echo "== inject: unbounded-repair (bare errors, no budget) =="
"$PY" -m toolargs.demo --seed 16 --inject unbounded-repair
echo
echo "== rule added: reason-in-record =="
"$PY" -m toolargs.demo --seed 16 --rule reason-in-record
echo
echo "== offline tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest toolargs.test_toolargs -v
