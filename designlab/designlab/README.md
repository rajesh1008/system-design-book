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
| `capacity/` | 10 | The Capacity Model on 90 days of pilot traces: task p95 against per-call p95, the latency budget and the model check; Chapter 44 adds `approvals`, the approval desk sized for a surge (seats for a promised wait, drain time, backlog by hour) |
| `isolation/` | 11 | Sessions, the sandbox runner, egress allow-lists (`isolation/egress.toml`) and the blast-radius probe |
| `failure/` | 12 | Fall 1 at scale: the key-per-attempt batch path, the ratio check, settlement, the fixed path and the breaker |
| `models/` | 13 | Model Contracts, golden sets, variance and amount reports, the drift check and recorded fixtures |
| `serving/` | 14 | Inference serving: the three clocks, batching, paged memory, prompt layout, the prefix cache and traveler salts, speculative decoding and the self-host cost |
| `portfolio/` | 15 | The Portfolio: steps and their gates, reasoning budgets, the Decision Table, the cascade and the router check |
| `toolargs/` | 16 | The tool-argument validation layer: shape checks, world checks and the layered repair budget |
| `adapt/` | 17 | The adaptation decision tree, distillation with a time split, preference pairs and verifiable rewards; teacher labels replay from `adapt/fixtures/` |
| `cost/` | 18 | Cost per verified outcome, the five levers, the caches, the budget enforcer and the driver forecast |
| `retrieval/` | 19, 24 | Lexical and dense retrievers fused by reciprocal rank, effective-date filters, a reranker, provenance, the bounded research loop with its sufficiency verifier, and the grounding check |
| `knowledge/` | 20 | The knowledge plane: a semantic layer of 41 metrics, the query guard (estimate, limits, entitlement, read-only run), and the itinerary graph |
| `context/` | 21 | The context assembler with a per-step budget and slot caps, pinned compaction and its verifier, isolation through sub-agents, instruction drift, and the context card |
| `memory/` | 22, 24 | The governed memory store: write gate, scope, provenance, supersession by compare-and-set, and deletion along `derived_from` links |
| `inputs/` | 23 | Input contracts at the edge for documents, images, voice, and web content |
| `knowops/` | 24 | Freshness contracts, the weekly fresh sample, memory expiry and supersession, and the destination verifier |
| `harness/` | 25 | The Harness Manifest (`harness/manifests/*.toml`): resolved, hashed, and registered before deploy; the loop two ways; and the harness test suite |
| `gateway/` | 26 | The tool registry and the gateway: description hashes, scope and argument checks, the policy hook, rate limits, code mode, and tool search |
| `topology/` | 27 | One agent against orchestrator-worker on the golden set, routing by legs, the talking stick across workers, hierarchy, voting, and the topology card |
| `loops/` | 28 | The unattended loop as data: the seven properties, the loops linter, the fare watch and waiver watch, the stall detector, and loop-day budgets |
| `sandbox/` | 29 | The escape battery, the review gate for coding-agent proposals, and a read-only browser reader |
| `runtimes/` | 30 | The runtimes comparison grid (`runtimes/grid.yaml`), two fixture adapters, the portability check, and skills with their drift check |
| `policy/` | 31 | The policy engine outside the loop: risk tiers, approval cards bound to the argument digest, temporal and sequence rules, effect budgets, signed bundles with shadow, and the three kill-switch tiers with drills |
| `identity/` | 32 | Per-run identity: run tokens minted at grant (delegation, not impersonation), the secret broker, data classes, the identity test and the trail check |
| `threats/` | 33 | The injection and poisoning battery: 61 attacks in six classes against an obedient stand-in model, the four controls (session binding, reply filter, egress, memory gate), the gateway's quote check, the trifecta and Rule of Two from configuration, and a recorded small-model replay |
| `evals/` | 34 | The release gate: a versioned golden set (640 tasks, eight classes), four-part scoring (outcome, trajectory, effects, forbidden effects), pass^k over three trials, a wording judge calibrated against people (kappa), online signals, and the improvement loop with release cuts |
| `tracing/` | 35 | The run as a trace: spans named by the GenAI semantic conventions with local `lakeshore.*` attributes and content by reference, the completeness check against the gateway trail, tail sampling, cost per decision and per harness version, the alerts, and strict and what-if replay |
| `assurance/` | 36 | Assurance on the record: period questions for the auditor answered from the trail, daily Merkle anchors held by audit, the sealed evidence pack with a seeded sample of chains, the June 24 production injection replayed, the destination-v1 rule, admissibility of evidence, and the finding from opened to closed |
| `reliability/` | 37 | Reliability on outcomes: five service objectives read from records the agent does not write, multiwindow burn-rate alerts on the rebooking slice, the error budget and freeze rule, the July 8 model update and the July 25 retry storm replayed, time to stop by kill-switch tier, the game day with one falsified hypothesis, runbooks, and reviews |
| `economics/` | 38 | The economics in operation: the July invoice by identity and the storm inside it, cost per verified outcome by kind of change, the worst case before the first call, spend policies at the model gateway with unknown usage settled at its worst case, the July 25 storm replayed in dollars, chargeback by identity, and the economics card |
| `release/` | 39 | Change and release: the six-kind bundle and hash, the rebuilt log (23 releases, two rolled back), regression as a gate with the split-payment adapter, what-if over recorded runs, canaries by task type on verified outcomes, rollback with runs in flight, shadow and fixed-horizon A/B, and the change card |
| `agentplatform/` | 40 | The agent platform: the project control plane of August 10 and why loyalty could not join it, the manifest template and its twelve problems, servicing and the desk extracted onto manifests, loyalty on the golden path, six conformance tests (K1 to K6) with the old ledger key failing K2, evidence-chain coverage, the two onboarding logs, platform economics and the charge table, and the platform card (named `agentplatform` because `platform` is a standard-library module) |
| `org/` | 41 | The team and its decision rights: the charter, seats and partners, the skills-to-planes gap analysis, the decision-rights matrix and six scenarios walked against three dated matrices (a seventh, the partner points transfer, fails until `usecase.transfer` is signed), the cost of a policy change nobody can approve, the operating rhythm, and the team card |
| `review/` | 42 | Architecture reviews: the production checklist by plane (sixteen items, executable over a design submission), the five gap questions, the verdict rule (a failing shape item declines, a failing value item changes), the decision record and its validator, the record store with its revisit queue, the review log, and the review card |
| `designs/` | 43 | Worked architectures: six customer-facing designs as data (telecom care, Lakeshore rebooking and refunds, bank payments, insurer claims, lender collections), templates that expand a design into Chapter 5's eight artifacts, a linter that runs `method.lint` plus eight worked rules (independent verifier, tier by amount, person gate, customer states, hand-off, obligations, economics), economics in seven lines with payback, the pattern table, faults for failure injection, and the worked card; extensible with `register` and `register_rule` |
| `golive/` | 44 | Go-live and the fall: the pilot and its numbers, the ramp by task type gated on verified outcomes against a ramp by traffic share, the storm day of September 10, 2026 as seeded records (41,000 changes in six hours), the approval queue replayed minute by minute with its order, seats, budget, kill-switch tier, and surge rule, named scenarios (as run, no prioritization, fare order, no emergency budget, autonomy widened, redesigned), the incident record as a trace, recovery measured, and the fall card with three changed designs |
| `ladder/` | 46 | The design interview as a ladder: seven levels and twelve prompts, the clock's four marks over Chapter 5's eight slices, twenty-four answer notes, the rubric (seven criteria, 0 to 2 each) and the component-list rubric it replaced, two-scorer calibration with exact agreement and kappa, the pinned small model as a third scorer (replayed), the timed drill with a mock interviewer (`models/interviewer.py`) held to a one-question contract, tiers onto levels, and the ladder card; extensible with `prompts.register` |
| `plan/` | 48 | The five-year plan as a decision record: the final card checked against itself, the four links named from a shipped design, the renaming table, what runtimes have absorbed and what stays, mandates that narrow down a hire chain, Lakeshore's year two (DR-48.1), the pinned-model window, and the plan linter (PLN-1 to PLN-9) with five faults |

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
    bash ch19/run.sh               # Chapter 19: retrieval and the research loop
    bash ch20/run.sh               # Chapter 20: the semantic layer and query guard
    bash ch21/run.sh               # Chapter 21: context budgets and compaction
    bash ch22/run.sh               # Chapter 22: the governed memory store
    bash ch23/run.sh               # Chapter 23: input contracts at the edge
    bash ch24/run.sh               # Chapter 24: the stale memory, injected and fixed
    bash ch25/run.sh               # Chapter 25: the Harness Manifest
    bash ch26/run.sh               # Chapter 26: the tool registry and gateway
    bash ch27/run.sh               # Chapter 27: one agent against orchestrator-worker
    bash ch28/run.sh               # Chapter 28: the fare watch as an unattended loop
    bash ch29/run.sh               # Chapter 29: escape battery and review gate
    bash ch30/run.sh               # Chapter 30: the runtimes grid and portability
    bash ch31/run.sh               # Chapter 31: policy, approvals, kill switch
    bash ch32/run.sh               # Chapter 32: identity, secrets, data classes
    bash ch33/run.sh               # Chapter 33: the injection and poisoning battery
    bash ch34/run.sh               # Chapter 34: the release gate and golden set
    bash ch35/run.sh               # Chapter 35: traces, cost, replay
    bash ch36/run.sh               # Chapter 36: evidence pack, injection, finding
    bash ch37/run.sh               # Chapter 37: objectives, budgets, incidents, runbooks
    bash ch38/run.sh               # Chapter 38: unit cost, budgets, spend policies, the bill
    bash ch39/run.sh               # Chapter 39: release bundle, canary, rollback, change card
    bash ch40/run.sh               # Chapter 40: the platform, paved road, conformance
    bash ch41/run.sh               # Chapter 41: roster, skills gap, decision rights, rhythm
    bash ch42/run.sh               # Chapter 42: checklist, verdict, decision records
    bash ch43/run.sh               # Chapter 43: six worked designs, linted, priced
    bash ch44/run.sh               # Chapter 44: the storm day replayed
    bash ch45/run.sh               # Chapter 45: six internal designs, linted
    bash ch46/run.sh               # Chapter 46: the interview ladder, drilled
    bash ch48/run.sh               # Chapter 48: final card, year-two plan, linted

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
