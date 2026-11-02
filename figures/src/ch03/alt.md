# ch03 alt text (one line per figure; copied into 03-figures/alt.md for the build)
fig-03-1: The seven categories of the map placed on the four planes, with frameworks, runtimes, and inference engines on the action plane, gateways and policy engines on the control plane, and evaluation tooling on the trail plane.
fig-03-2: A table of seven frameworks and SDKs showing the loop shape each one decides, where its permission hook runs (in the agent's own process for all seven), and its version line, with the pre-1.0 versions hatched.
fig-03-3: A table of five hosted runtimes showing which of sessions, policy, traces, and the effect ledger each one hosts, partly hosts, or leaves to the customer; the ledger is left to the customer by all five.
fig-03-4: A top-to-bottom flow from an agent through MCP to tools, through A2A to a remote agent, and through an AP2 mandate signed on a trusted surface to a merchant reached over ACP or x402, each protocol labeled with its version and date.
fig-03-5: A top-to-bottom diagram in which the registry feeds the gateway, the gateway asks a Cedar or OPA policy engine outside the agent loop, and the engine writes a decision log.
fig-03-6: A table of inference engines (vLLM, SGLang, TensorRT-LLM) and the cluster layers above them (Dynamo and llm-d), by deployment shape.
fig-03-7: Agent spans flow into a trace store read by an evaluator, while a separate read-only verifier reads the reservation system to produce the verified outcome that the evaluator never sees.
fig-03-8: A heat grid of 31 options by five gaps, generated from map.yaml, in which no option closes the execution-to-outcome or outcome-to-result gaps.
fig-03-9: The shortlist decision table with each runtime and framework, its score, and its lock-in, with three runtimes and two frameworks shortlisted and the others marked lower score, beta, or pre-1.0.
