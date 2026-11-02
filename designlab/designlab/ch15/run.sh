#!/usr/bin/env bash
# Chapter 15 lab: offline tests, the steps and their gates on recorded
# calls, the reasoning budgets, the decision table, the cascade, the
# router check on forty tasks, and the cost-only rule (which must fail
# the check), then the scorecard and the secret scan. No live API is
# used here.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest \
  portfolio.test_portfolio portfolio.test_live
python3 -m portfolio.demo steps
python3 -m portfolio.demo gate
python3 -m portfolio.demo budget
python3 -m portfolio.demo table
python3 -m portfolio.demo cascade
python3 -m portfolio.demo check
if python3 -m portfolio.demo check --rule cost-only; then
  echo "the cost-only rule did not fail the check" >&2
  exit 1
fi
echo "the cost-only rule failed the check, as it should"
python3 -m portfolio.demo table --rule cost-only
python3 -m portfolio.demo scorecard
python3 -m common.secretscan
