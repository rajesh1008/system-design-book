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
| `ch01/` | 1 | designlab v0: one action end to end, with a policy check outside the loop, an idempotency key, a reconciler that did not act, and the trail checker |
| `chain/` | 2 | The chain record and a loop that refuses an effect without its evidence |
| `map/` | 3 | The map of the agent field as dated data (`map/map.yaml`) and the shortlist scorer |
| `baseline/` | 4 | Lakeshore before any agent: volume, mix, cost per change, refund error and the honest automation rate |
| `method/` | 5 | The eight design artifacts, the Estimate Sheet (`method/designs/*.toml`) and the design linter |
| `planes/` | 6 | The four planes, contracts C1 to C6, the path test and the autonomy table |
| `effects/` | 7 | The Effect Ledger: nine states, tool contracts (native, lookup, none), the reconciler sweep and replay with a no-key injection |
| `spine/` | 8 | The asynchronous spine: per-itinerary ordering, the talking stick, backpressure on approvals, dead letters and an airline-cancellation fan-out |
| `durable/` | 9 | The run store: checkpoints, the journal, strict and what-if replay, the kill suite and durable timers |
| `capacity/` | 10 | The Capacity Model on 90 days of pilot traces: task p95 against per-call p95, the latency budget and the model check |
| `isolation/` | 11 | Sessions, the sandbox runner, egress allow-lists (`isolation/egress.toml`) and the blast-radius probe |
| `failure/` | 12 | Fall 1 at scale: the key-per-attempt batch path, the ratio check, settlement, the fixed path and the breaker |
| `models/` | 13 | Model Contracts, golden sets, variance and amount reports, the drift check and recorded fixtures |
| `serving/` | 14 | Inference serving: the three clocks, batching, paged memory, prompt layout, the prefix cache and traveler salts, speculative decoding and the self-host cost |
| `portfolio/` | 15 | The Portfolio: steps and their gates, reasoning budgets, the Decision Table, the cascade and the router check |
| `toolargs/` | 16 | The tool-argument validation layer: shape checks, world checks and the layered repair budget |
| `adapt/` | 17 | The adaptation decision tree, distillation with a time split, preference pairs and verifiable rewards; teacher labels replay from `adapt/fixtures/` |
| `cost/` | 18 | Cost per verified outcome, the five levers, the caches, the budget enforcer and the driver forecast |
| `policy/` | 31 | The policy engine outside the loop: risk tiers, approval cards bound to the argument digest, temporal and sequence rules, effect budgets, signed bundles with shadow, and the three kill-switch tiers with drills |
| `identity/` | 32 | Per-run identity: run tokens minted at grant (delegation, not impersonation), the secret broker, data classes, the identity test and the trail check |

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
    python3 -m ch01.demo           # Chapter 1: one action end to end
    python3 -m chain.demo          # Chapter 2: the refund that happened twice
    python3 -m map.demo            # Chapter 3: the map as data
    python3 -m baseline.demo       # Chapter 4: the baseline from operations data
    python3 -m method.demo         # Chapter 5: lint designs, the estimate sheet
    python3 -m planes.demo         # Chapter 6: the four planes and six contracts
    bash ch07/run.sh               # Chapter 7: the Effect Ledger
    bash ch08/run.sh               # Chapter 8: the asynchronous spine
    bash ch09/run.sh               # Chapter 9: checkpoints, replay, the killed process
    bash ch10/run.sh               # Chapter 10: the Capacity Model
    bash ch11/run.sh               # Chapter 11: isolation and blast radius
    bash ch12/run.sh               # Chapter 12: the refund failure at scale
    bash ch13/run.sh               # Chapter 13: Model Contracts and the drift check
    bash ch14/run.sh               # Chapter 14: inference serving
    bash ch15/run.sh               # Chapter 15: the Portfolio and the router
    bash ch16/run.sh               # Chapter 16: tool-argument validation
    bash ch17/run.sh               # Chapter 17: adaptation and distillation
    bash ch18/run.sh               # Chapter 18: cost and budget enforcement
    bash ch31/run.sh               # Chapter 31: policy, approvals, kill switch
    bash ch32/run.sh               # Chapter 32: identity, secrets, data classes

Each chapter also has a script that runs its tests and demos, for example
`bash ch05/run.sh`.

## Tests

    ./run_all.sh

This runs the offline unit tests, then every live test if `ANTHROPIC_API_KEY`
is set, then the Part I demos offline, then a secret scan of the whole tree. Without a key the live tests
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
