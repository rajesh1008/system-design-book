#!/usr/bin/env bash
# Chapter 38 lab: the July invoice and the storm inside it, cost per
# verified outcome by kind of change, the worst case before the run,
# spend policies at the model gateway, the storm replayed under them,
# chargeback by identity, and the economics card. Offline; no model
# call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in invoice close kinds weekly bound storm policy; do
    "$PY" -m economics.demo --part "$part"
    echo
done
"$PY" -m economics.demo --part close --rule identity
echo
"$PY" -m economics.demo --part kinds --month August
echo
"$PY" -m economics.demo --part policy --envelope 200
echo
"$PY" -m economics.demo --part chargeback --rule pool
echo
for part in chargeback august card; do
    "$PY" -m economics.demo --part "$part"
    echo
done
"$PY" -m economics.demo --part chargeback --by use-case
echo
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest economics.test_economics -v
