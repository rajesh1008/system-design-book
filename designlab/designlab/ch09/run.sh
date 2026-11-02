#!/usr/bin/env bash
# Chapter 9 lab: checkpoints, replay, and the killed process. Offline
# tests, the March restart both ways, the kill suite, the injection,
# replay, the week-long wait, the benchmark, the card, then the secret
# scan. No live API calls.
set -euo pipefail
cd "$(dirname "$0")/.."
DESIGNLAB_OFFLINE=1 python3 -m unittest durable.test_durable
python3 -m durable.demo incident
python3 -m durable.demo kill
python3 -m durable.demo inject
python3 -m durable.demo replay
python3 -m durable.demo wait
python3 -m durable.demo bench
python3 -m durable.demo card
python3 -m common.secretscan
