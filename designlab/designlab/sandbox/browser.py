"""A read-only computer-use reader for supplier portals with no API.

The reader works the way a computer-use agent works: look at the page,
decide one action, act, look again. The portals here are fixtures and
the model is replaced by a scripted policy, so the lab measures the
shape of the work (steps, refusals, unknowns), not a model. Step costs
are the lab's illustrative settings, not measurements of any product.

The reader's role is read only. It may load pages on the portal's own
host, fill the login and search fields (the login secret is filled by
the broker outside the sandbox, never shown to the reader), and press
buttons marked as search or open. Any other submit is refused. Any
link to another host goes through the egress policy and is refused.
When it cannot find the status, it answers "unknown", never a guess.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from html.parser import HTMLParser

from common.trail import TrailWriter
from isolation.egress import EgressPolicy

TOOL = "browser_read"
PORTALS = {"crescent": "partners.crescenthotels.example",
           "prairie": "extranet.prairielodge.example"}
POLICY = {"version": "2026-06-08", "owner": "Owen Fletcher",
          "host": [{"name": h, "port": 443, "tools": [TOOL],
                    "reason": "supplier extranet, read only"}
                   for h in PORTALS.values()]}

LOOK_S = (4.2, 6.4)     # screenshot plus one model turn, illustrative
LOAD_S = (0.6, 1.4)     # page load, illustrative
API_S = 0.4             # one API call to a supplier that has one


def page(host: str, ref: str, status: str, label: str = "Status",
         note: str = "") -> dict[str, str]:
    base = f"https://{host}"
    return {
        f"{base}/login": (
            '<form role="login"><input name="user"><input name="pass">'
            '<button role="login" href="/home">Sign in</button></form>'),
        f"{base}/home": (
            '<form role="search"><input name="conf">'
            '<button role="search" href="/res">Find</button></form>'
            '<a href="/reports">Reports</a><a href="/rates">Rates</a>'),
        f"{base}/res": (
            f'<a role="open" href="/res/{ref}">{ref}</a>'),
        f"{base}/res/{ref}": (
            f'<h1>Reservation {ref}</h1><p>Guest: L. Ortiz</p>'
            f'<p>{label}: {status}</p><p>Notes: {note}</p>'
            '<button role="submit" href="/res/cancel">Cancel '
            'reservation</button>'
            '<button role="submit" href="/res/confirm">Confirm</button>'),
    }


class _Page(HTMLParser):
    def __init__(self, html: str):
        super().__init__()
        self.text: list[str] = []
        self.controls: list[dict] = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("a", "button"):
            self.controls.append({"tag": tag, **a})

    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())


@dataclass
class Check:
    ref: str
    answer: str          # cancelled | active | unknown
    steps: int
    seconds: float
    refused: list[str] = field(default_factory=list)


class Reader:
    def __init__(self, portal: str, pages: dict[str, str],
                 seed: int = 29):
        self.host = PORTALS[portal]
        self.pages = pages
        self.rng = random.Random(seed)
        self.trail = TrailWriter()
        self.egress = EgressPolicy(POLICY, self.trail)

    def _step(self) -> float:
        return self.rng.uniform(*LOOK_S) + self.rng.uniform(*LOAD_S)

    def _go(self, url: str, c: Check) -> _Page | None:
        if url.startswith("/"):
            url = f"https://{self.host}{url}"
        v = self.egress.check(TOOL, url, c.ref)
        c.steps += 1
        c.seconds += self._step()
        if not v.allowed:
            c.refused.append(f"navigate {v.host}: {v.reason}")
            return None
        return _Page(self.pages.get(url, "<p>Not found</p>"))

    def press(self, ctl: dict, c: Check) -> _Page | None:
        if ctl.get("role") not in ("login", "search", "open", None):
            c.steps += 1
            c.seconds += self._step()
            c.refused.append(f"press '{ctl.get('href')}': submit "
                             f"not in read-only role")
            return None
        return self._go(ctl["href"], c)

    def status(self, ref: str, follow_notes: bool = True) -> Check:
        """Scripted policy: sign in, search, open, read. With
        follow_notes, it also does what the page's notes ask (a model
        might): open a link, press Confirm. The role and egress
        decide what happens."""
        c = Check(ref, "unknown", 0, 0.0)
        p = self._go("/login", c)
        c.steps += 2                       # two fields, broker fills
        c.seconds += 2 * self._step()
        for want in ("login", "search", "open"):
            ctl = next((x for x in p.controls if x.get("role") == want),
                       None)
            if ctl is None:
                return c
            if want == "search":
                c.steps += 1               # type the confirmation code
                c.seconds += self._step()
            p = self.press(ctl, c)
            if p is None:
                return c
        text = " ".join(p.text)
        if follow_notes and "http" in text:
            url = "https://" + text.split("https://", 1)[1].split()[0]
            self._go(url, c)
        if follow_notes and "press Confirm" in text:
            for ctl in p.controls:
                if "confirm" in ctl.get("href", ""):
                    self.press(ctl, c)
        c.steps += 1                       # final look and answer
        c.seconds += self._step()
        for chunk in p.text:
            if chunk.startswith("Status:"):
                v = chunk.split(":", 1)[1].strip().lower()
                c.answer = v if v in ("cancelled", "active") else "unknown"
        return c


def compare(n: int = 25, seed: int = 29) -> dict:
    """n status checks through the reader against n API calls."""
    pages = page(PORTALS["crescent"], "CH-48213", "Cancelled")
    r = Reader("crescent", pages, seed)
    runs = [r.status("CH-48213") for _ in range(n)]
    secs = sorted(x.seconds for x in runs)
    return {"n": n, "steps": runs[0].steps,
            "median_s": statistics.median(secs),
            "p95_s": secs[int(0.95 * (n - 1))],
            "api_s": API_S, "answers": {x.answer for x in runs}}
