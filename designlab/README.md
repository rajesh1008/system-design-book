# designlab code

The labs for *System Design for Agentic AI* live in [`designlab/`](designlab/).
They need Python 3.11 or later and nothing else.

    cd designlab
    ./run_all.sh              # tests: offline, then live if a key is set
    python3 -m corpus.demo    # any lab: common, corpus, bank, chain

See [`designlab/README.md`](designlab/README.md) for the module list,
install steps, every lab command, the pinned model IDs and how live calls
are kept safe and cheap.
