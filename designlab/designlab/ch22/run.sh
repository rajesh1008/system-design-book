#!/usr/bin/env bash
# Chapter 22 lab: the governed memory store. Offline; no key needed.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== the governed memory store, seed 22 =="
"$PY" -m memory.demo --seed 22
echo
echo "== failure injection: a memory written without provenance =="
"$PY" -m memory.demo --no-provenance
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest memory.test_memory -v
