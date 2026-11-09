#!/usr/bin/env bash
# Chapter 42 lab: the checklist and decision records. Offline.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m review.demo --part gaps
"$PY" -m review.demo --part checklist
"$PY" -m review.demo --part verdict
"$PY" -m review.demo --part verdict --inject self-verify
"$PY" -m review.demo --part gaps --design points-transfer-v2
"$PY" -m review.demo --part checklist --design points-transfer-v2
"$PY" -m review.demo --part verdict --design points-transfer-v2
"$PY" -m review.demo --part verdict --design points-transfer-v2 \
  --conditions
"$PY" -m review.demo --part record --minutes
"$PY" -m review.demo --part store
"$PY" -m review.demo --part store --as-of 2026-12-31
"$PY" -m review.demo --part verdict --inject no-kill-switch
"$PY" -m review.demo --part log
"$PY" -m review.demo --part card
DESIGNLAB_OFFLINE=1 "$PY" -m unittest review.test_review -v
