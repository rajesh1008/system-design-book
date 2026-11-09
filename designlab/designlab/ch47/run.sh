#!/usr/bin/env bash
# Chapter 47 lab: the interview bank over the whole book. Reads every
# chapter's interview section (or, where the manuscript is absent, as
# in the public repository, the committed metadata index), routes each
# question to one of nine round tags, prints the card and the
# hiring-side minimum, reads the control round's two notes, builds the
# two loops for the January 2027 requisitions, injects a question with
# no chapter (the generator refuses it), renders Appendix J, and runs
# the Try It Yourself filters and the tests. Offline; no model is
# called and no key is read.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-python3}
for part in source rounds card short notes loop fault appendix \
        filter sixty parts; do
    "$PY" -m bank.demo47 --part "$part"
    echo
done
echo "== tests =="
DESIGNLAB_OFFLINE=1 "$PY" -m unittest bank.test_ch47 bank.test_bank -v
