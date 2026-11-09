#!/usr/bin/env bash
# Chapter 43 lab: six worked designs (telecom care, Lakeshore
# rebooking, Lakeshore refunds, bank payments, insurer claims, lender
# collections) linted by the book's own method; the failure injection
# (the acting agent verifies its own effect); the Try It Yourself runs
# (a bank limit moved, the collections gate removed, a seventh
# industry); the customer's six states; the patterns that recur; the
# cost per verified outcome; and the worked card. Offline; no model
# call and no key.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
"$PY" -m designs.demo --part method
echo
"$PY" -m designs.demo --part design --id bank-payments
echo
"$PY" -m designs.demo --part lint
echo
# Failure injection: each of these is expected to fail the linter.
"$PY" -m designs.demo --part lint --fault actor-verifies || true
echo
"$PY" -m designs.demo --part lint --set \
    bank-payments:transfer.limit_usd=2500 || true
echo
"$PY" -m designs.demo --part lint --fault no-gate || true
echo
"$PY" -m designs.demo --part lint --add designs/data/_seventh.toml \
    || true
echo
for part in states patterns cost card; do
    "$PY" -m designs.demo --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest designs.test_designs -v
