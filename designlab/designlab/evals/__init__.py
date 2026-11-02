"""Evaluation as a release gate (Chapter 34).

Golden tasks that score four things (outcome, tool sequence, effects,
forbidden effects), a trajectory matcher, a model judge calibrated
against people's labels, pass^k, online scoring of production traces,
a trace harvest that proposes candidate tasks, and the release gate
that runs all of it before a release ships. Reuses harness (cases,
the refund world, manifests), common (client, text) and models.
"""
