"""designlab.serving: the inference layer as a component (Chapter 14).

Three clocks of a request, static and continuous batching, a paged
KV allocator, a prefix cache in two forms (a provider's prompt cache
with breakpoints and a time to live, and an engine's block cache with
least-recently-used eviction), a prompt-layout linter, speculative
decoding arithmetic, a toy prefill/decode split, the bake-off over
recorded fixtures, and the self-hosted versus API cost comparison.

Standard library and `common` only. No model is called.
"""
