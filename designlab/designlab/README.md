# designlab

The small reference system that accompanies *System Design for Agentic AI*.
Every chapter adds or replaces one part. It uses only the Python standard
library (3.11 or later). Nothing needs an API key unless a lab says so, and
the key is read from the environment only.

| Package | Chapters | What it holds |
|---|---|---|
| `common/` | all | Run ids, a fixed clock, seeded randomness, the hash-linked trail, redaction, the spend meter, pinned model IDs (`common/models.toml`) and the model client |
| `corpus/` | 4, 7, 10, 19, 34, 44 | The synthetic Lakeshore Travel Group data, v0, generated from a seed |
| `bank/` | 41, 47 | The interview-bank schema, loader and index generator, v0 |
| `chain/` | 2 | The chain record and a loop that refuses an effect without its evidence |

## Install

    git clone https://github.com/rajesh1008/system-design-book
    cd system-design-book/designlab/designlab
    python3 --version              # 3.11 or later

There is nothing else to install. To use the packages from another directory,
install them into a virtual environment (the package names are short, so keep
them out of your system Python):

    python3 -m venv .venv && . .venv/bin/activate
    pip install .

## Run the labs

From this directory:

    python3 -m common.demo         # trail, redaction, spend cap (offline)
    python3 -m corpus.demo         # the Lakeshore corpus: sizes and ratios
    python3 -m corpus.build        # write it to out/corpus/ as JSON Lines
    python3 -m corpus.build --scale full     # ten times larger
    python3 -m bank.demo           # load, index and check interview questions
    python3 -m bank.index FILE.md  # print the interview index for a bank file
    python3 -m chain.demo          # Chapter 2: the refund that happened twice

## Tests

    ./run_all.sh

This runs the offline unit tests, then the live tests if `ANTHROPIC_API_KEY`
is set, then a secret scan of the whole tree. Without a key the live tests
skip cleanly; set `DESIGNLAB_OFFLINE=1` to skip them even with a key. A full
live run makes six short calls and costs well under one cent.

## Live calls

    export ANTHROPIC_API_KEY=...   # never commit it, never paste it in a file
    python3 -m common.probe        # one eight-token call per pinned model

The client sends the key in one request header and nowhere else. Every call
is checked against a spend cap ($2.00 by default) before it is sent. Cached
responses and recorded fixtures are redacted and never hold request headers.

## Pinned models

Code asks for a role, never a model name. The IDs below were listed by the
provider and answered a live call on November 2, 2026. They change only
through the release gate (Chapter 39).

| Role | Model ID |
|---|---|
| small | `claude-haiku-5-5` |
| mid | `claude-sonnet-5-5` |
| frontier | `claude-opus-5-5` |
| dated | `claude-haiku-4-5-20251001` |

## The corpus

`corpus.generate(seed=2026)` returns fourteen tables: carriers, airports,
hotels, policies, customers, flights, itineraries, contacts, changes,
refunds, settlement lines, tickets, hotel emails and memories. The same seed
always gives the same bytes; the manifest's digest names them. Every company
and person is invented, customer email addresses use `example.com`, and the
airport codes are real places only. Generated files go to `out/`, which git
ignores.

Test results from the last full run are in `TEST-RESULTS.md`.
