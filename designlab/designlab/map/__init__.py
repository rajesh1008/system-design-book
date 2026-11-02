"""The map (Chapter 3): every option in the agent field as dated data.

    map.yaml     the options, their gap coverage and their dated claims
    yamlish.py   a small YAML-subset reader (standard library only)
    model.py     load and validate: a claim without a date is refused
    shortlist.py score options against the five gaps and pick a shortlist
    demo.py      python3 -m map.demo
"""
