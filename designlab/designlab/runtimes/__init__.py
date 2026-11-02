"""Runtimes (Chapter 30): build, buy, or rent, as data and tests.

    grid.yaml       the June 2026 bake-off: 5 options, 22 dated criteria
    grid.py         load and validate the grid; score it by plane
    adapters.py     two fixture runtimes with different session models
    portability.py  the harness on both adapters; the migration test
    skills.py       skills and instruction files: disclosure and drift
    demo.py         python3 -m runtimes.demo --part grid

No live API calls. The adapters replay synthetic fixtures shaped on
two documented session models; they are not vendor recordings.
"""
