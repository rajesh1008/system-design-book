"""Tokenizing shared by every retriever, so they disagree on ranking,
not on what a word is."""
from __future__ import annotations

import re

STOP = frozenset("""a an and are as at be by can do does for from has have
how i if in is it its my of on or our so that the their this to was we
what when which will with you your me may per any after before than
then they them about into get our us also""".split())

_WORD = re.compile(r"[a-z0-9$]+")


def stem(w: str) -> str:
    for suf in ("ings", "ing", "ies", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokens(text: str) -> list[str]:
    out = []
    for w in _WORD.findall(text.lower().replace("-", " ")):
        w = w.lstrip("$")
        if w and w not in STOP:
            out.append(stem(w))
    return out
