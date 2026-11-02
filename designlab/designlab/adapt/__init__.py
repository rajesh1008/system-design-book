"""Adapting a model as a design decision (Chapter 17).

`tree.py` walks a request to adapt a model through the decision tree:
name the failure, try context, try tools and contracts, and adapt only a
narrow step that can be measured. `data.py` builds six months of change
requests; `learn.py` is TF-IDF and logistic regression by hand, the
stand-in for a small distilled model; `evaluate.py` splits by time,
checks overlap, and compares the student with the frontier teacher;
`teacher.py` collects frontier labels live (or replays them);
`cost.py` prices a step; `prefs.py` turns approver corrections into
preference pairs; `reward.py` shows a verifiable reward and a hackable one.
"""
