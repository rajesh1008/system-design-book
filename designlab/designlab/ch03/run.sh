#!/usr/bin/env bash
# Chapter 3 lab: the map as data. Offline tests, the demo, the two
# Try It Yourself variations, then the secret scan. No live API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest map.test_map
python3 -m map.demo
python3 -m map.demo --today 2027-05-02 | sed -n '/^5\./,/^6\./p'
python3 -m map.demo --lockin-weight 2 | sed -n '/^5\./,/^6\./p'
python3 -m common.secretscan
