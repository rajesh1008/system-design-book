"""A model judge for customer-message wording, calibrated against people.

The judge reads only the message. It scores wording against a rubric:
the outcome, the amount and where it goes, what happens next, and no
promise beyond policy. It never scores effects; the ledger does that.
`OfflineJudge` stands in for a model judge with the biases model
judges are known for (it likes fluent, reassuring text and forgives a
missing next step). Calibration measures its agreement with people's
labels on a held-out set, refuses labels that came from the judge
itself, and is valid only for the judge's model pin.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

KAPPA_MIN = 0.75


def render(m: dict) -> str:
    """The message text a customer, a person, or a live judge reads."""
    kind = m["kind"]
    if m.get("terse"):
        return {"refunded": "Refund done.", "declined": "Not refundable.",
                "not_approved": "Refund not approved.",
                "already_refunded": "Already refunded."}.get(kind, "Sent.")
    if kind == "refunded" and m.get("explains"):
        s = (f"Because the card you paid with has expired, your refund "
             f"of ${m['amount']:.2f} goes to the card on file ending "
             f"{m['card']}, so you do not wait on the old card.")
        nxt = " It should reach you in five to seven business days."
    elif kind == "refunded":
        s = (f"Your refund of ${m['amount']:.2f} goes back to the card "
             f"ending {m['card']}.")
        nxt = " It should reach you in five to seven business days."
    elif kind == "declined":
        s = "Your fare's rules do not allow a refund for this change."
        nxt = " You can still use the ticket's value as credit for a year."
    elif kind == "not_approved":
        s = "Our refunds team reviewed the request and did not approve it."
        nxt = " A team lead will call you within one business day."
    elif kind == "already_refunded":
        s = (f"This booking was already refunded ${m['amount']:.2f} "
             f"to the card ending {m['card'] or 'on the booking'}.")
        nxt = " It should reach you in five to seven business days."
    else:
        s, nxt = "A person on our desk will take this from here.", ""
    if not m.get("timeline"):
        nxt = ""
    extra = (" We have also waived any change fee on your next trip."
             if m.get("overpromise") else "")
    return "Thank you for your patience. " + s + nxt + extra


def people_label(m: dict) -> bool:
    """The rubric as the desk applies it."""
    return (not m.get("terse") and bool(m.get("timeline"))
            and not m.get("overpromise"))


@dataclass(frozen=True)
class OfflineJudge:
    id: str = "judge:wording"
    pin: str = "small@2026-05-12"

    def score(self, key: str, m: dict) -> int:
        """1 to 10. Reads the message only."""
        noise = random.Random(f"{self.pin}:{key}").uniform(-0.73, 0.73)
        s = (4 + 2 * (not m.get("terse")) + 2 * bool(m.get("timeline"))
             + 1.5 * bool(m.get("overpromise"))
             + 1 * bool(m.get("explains")) + noise)
        return max(1, min(10, round(s)))

    def passes(self, key: str, m: dict) -> bool:
        return self.score(key, m) >= 7


def kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


class NotCalibrated(RuntimeError):
    pass


@dataclass(frozen=True)
class Calibration:
    judge: str
    pin: str
    label_source: str
    n: int
    agreement: float
    kappa: float

    def valid_for(self, judge) -> bool:
        return (judge.id == self.judge and judge.pin == self.pin
                and self.kappa >= KAPPA_MIN)


def calibrate(judge, items: list[tuple[str, dict]], labels: list[bool],
              label_source: str, force: bool = False) -> Calibration:
    """Agreement between the judge and labels on held-out items."""
    if label_source == judge.id and not force:
        raise NotCalibrated("labels came from the judge being calibrated")
    got = [judge.passes(k, m) for k, m in items]
    agree = sum(g == h for g, h in zip(got, labels)) / len(labels)
    return Calibration(judge.id, judge.pin, label_source, len(labels),
                       agree, kappa(got, labels))
