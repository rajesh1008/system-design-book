#!/usr/bin/env bash
# Chapter 10 lab: the Capacity Model on 90 days of pilot traces.
# Offline tests, the demo, the injected failure (a task p95 predicted
# from the per-call p95), the three Try It Yourself variations, then the
# secret scan. Seed 10. No live API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest capacity.test_capacity
python3 -m capacity.demo --seed 10
python3 -m capacity.demo --seed 10 --session S018387
python3 -m capacity.demo --seed 10 --part predict --inject per-call \
  || echo "exit 1: the model check failed, as injected"
python3 -m capacity.demo --seed 10 --part budget --retry-scale 2
python3 -m capacity.demo --seed 10 --part surge --util 0.95 \
  | sed -n '/^5\./,/Kingman/p'
python3 -m capacity.demo --seed 10 --part budget --prefetch
python3 -m common.secretscan
