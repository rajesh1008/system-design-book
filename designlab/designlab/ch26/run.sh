#!/usr/bin/env bash
# Chapter 26 lab: the tool registry and the gateway. Offline; no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== registry, gateway, code mode and search, seed 26 =="
"$PY" -m gateway.demo --tools 400
echo
echo "== try it: a served description changes after review =="
"$PY" -m gateway.demo --change-description
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest gateway.test_gateway -v
