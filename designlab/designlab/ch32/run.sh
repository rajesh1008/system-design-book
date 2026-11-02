#!/usr/bin/env bash
# Chapter 32 lab: per-run identity, delegation, the secret broker, data
# classes, and the trail check. Offline; no API key is used.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
echo "== June 16 access review: the standing account =="
"$PY" -m identity.demo --part found
echo
echo "== one run, one refund, on a run token =="
"$PY" -m identity.demo --part mint
echo
echo "== what the run token refuses =="
"$PY" -m identity.demo --part probes
echo
echo "== the secret broker and the context check =="
"$PY" -m identity.demo --part broker
echo
echo "== data classes on 200 seeded cases =="
"$PY" -m identity.demo --part data
echo
echo "== exposure by token lifetime =="
"$PY" -m identity.demo --part exposure
echo
echo "== try it: tokens found faster (median 10 min) =="
"$PY" -m identity.demo --part exposure --median 10
echo
echo "== injection: a standing payments write credential =="
"$PY" -m identity.demo --part inject
echo
echo "== the trail check =="
"$PY" -m identity.demo --part check
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest identity.test_identity -v
