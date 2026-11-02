#!/usr/bin/env bash
# Chapter 13 lab: offline tests, the contract suites on recorded
# fixtures, the variance and amount reports, the drift check, and two
# injected model moves (which must fail the drift check), then the
# secret scan. No live API is used here.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest \
  models.test_models models.test_live
python3 -m models.demo contracts
python3 -m models.demo test
python3 -m models.demo format
python3 -m models.demo variance
python3 -m models.demo amount
python3 -m models.demo drift
for inj in silent alias; do
  if python3 -m models.demo drift --inject "$inj"; then
    echo "injection $inj did not fail the drift check" >&2
    exit 1
  fi
done
echo "both injections failed the drift check, as they should"
python3 -m models.demo naive
python3 -m common.secretscan
