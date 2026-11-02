# designlab

The small reference system that accompanies *System Design for Agentic AI*.
Every chapter adds or replaces one part. Nothing here needs an API key unless a
lab says so, and any key is read from the environment only.

| Package | Chapter | What it holds |
|---|---|---|
| `chain/` | 2 | The chain record and a loop that refuses an effect without its evidence |

Run the chapter 2 lab and its tests from this directory:

    python3 -m chain.demo
    python3 -m unittest chain.test_chain -v
