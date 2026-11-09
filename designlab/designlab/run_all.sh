#!/usr/bin/env bash
# Run every designlab test from this directory.
#   1. offline unit tests (live tests forced to skip)
#   2. live tests (every test_live*.py), only when RUN_LIVE=1 and
#      ANTHROPIC_API_KEY are both set (a few cents at most); a key in
#      the environment alone never starts a live call
#   3. the Part I demos, offline, as a smoke run
#   4. the secret scan over the whole tree, fixtures included
set -euo pipefail
cd "$(dirname "$0")"
PY=${PYTHON:-python3}

echo "== offline unit tests"
DESIGNLAB_OFFLINE=1 "$PY" -m unittest discover -s . -t . -p 'test_*.py' -v

echo "== live tests"
if [ "${RUN_LIVE:-0}" = "1" ] && [ -n "${ANTHROPIC_API_KEY:-}" ] \
    && [ "${DESIGNLAB_OFFLINE:-0}" != "1" ]; then
  "$PY" -m unittest discover -s . -t . -p 'test_live*.py' -v
else
  echo "live tests skipped (set RUN_LIVE=1 and ANTHROPIC_API_KEY to run)"
fi

echo "== Part I demos (offline)"
for m in ch01.demo chain.demo map.demo baseline.demo method.demo planes.demo; do
  DESIGNLAB_OFFLINE=1 "$PY" -m "$m" > /dev/null && echo "ok  $m"
done

echo "== secret scan"
"$PY" -m common.secretscan
