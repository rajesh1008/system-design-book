#!/usr/bin/env bash
# Chapter 23: multimodal inputs and the trust boundary at the edge.
# Offline. The two live labs replay recorded fixtures here; to record
# again, python3 -m inputs.live --record and python3 -m models.vision
# --record need ANTHROPIC_API_KEY in the environment (under a cent).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}

echo "== the three inputs Owen laid side by side =="
"$PY" -m inputs.demo --part opening
echo
echo "== the red-team letter through the contract =="
"$PY" -m inputs.demo --part letter
echo
echo "== inject: instruction-as-text (the edge skipped) =="
"$PY" -m inputs.demo --part letter --inject instruction-as-text
echo
echo "== eight documents, pilot prompt against contract (recorded) =="
"$PY" -m inputs.live
echo
echo "== a boarding pass with a note in the margin =="
"$PY" -m inputs.demo --part boarding
echo
echo "== the same pass read from pixels by a model (recorded) =="
"$PY" -m models.vision
"$PY" -m inputs.demo --part vision
echo
echo "== thresholds and the record check =="
"$PY" -m inputs.demo --part thresholds
echo
echo "== voice turn latency, batch and streaming =="
"$PY" -m inputs.demo --part voice --batch
"$PY" -m inputs.demo --part voice
echo
echo "== read-back of amounts and dates =="
"$PY" -m inputs.demo --part readback --off
"$PY" -m inputs.demo --part readback
echo
echo "== a carrier notice page with hidden text =="
"$PY" -m inputs.demo --part web
echo
echo "== edge test: every intake path =="
"$PY" -m inputs.demo --part edge
echo
echo "== the input card =="
"$PY" -m inputs.demo --part card
echo
echo "== offline tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest inputs.test_inputs \
  inputs.test_live_inputs models.test_vision models.test_live_vision -v
