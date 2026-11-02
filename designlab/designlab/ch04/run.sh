#!/usr/bin/env bash
# Chapter 4 lab: the baseline from operations data. Offline tests, the
# demo, the injected failure (an automation rate that counts hand-offs),
# the three Try It Yourself variations, then the secret scan. No live
# API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest corpus.test_ops baseline.test_baseline
python3 -m baseline.demo
python3 -m baseline.demo --inject vendor | sed -n '/^4\./,/^5\./p' \
  || echo "exit 1: the metric test failed, as injected"
python3 -m baseline.demo --person-cost 1.1 | sed -n '/^2\./,/^3\./p'
python3 -m baseline.demo --count-abandons | sed -n '/^4\./,/incidents/p'
python3 -m baseline.demo --by-carrier | sed -n '/worst/,/^4\./p'
python3 -m common.secretscan
