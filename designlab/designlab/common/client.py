"""The model client every live lab goes through.

- The key is read from ANTHROPIC_API_KEY at call time, placed in one
  request header and nowhere else. It is never printed, logged, cached,
  written to a fixture, or included in an exception.
- Every call is checked against the spend meter before it is sent and
  priced from the response's usage after it returns.
- Responses can be cached and recorded as fixtures. Both store the
  request body and the response, redacted; request headers are never
  stored.
- `FixtureTransport` replays recorded fixtures, so offline tests exercise
  the same code path without a key.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .live import KEY_ENV
from .models import ModelPin, api_version, pin
from .redact import redact, redact_text
from .spend import SpendMeter

API_URL = "https://api.anthropic.com/v1/messages"
Transport = Callable[[dict], dict]


class MissingKey(RuntimeError):
    pass


class APIError(RuntimeError):
    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"HTTP {status}: {redact_text(message)[:200]}")


class NoFixture(LookupError):
    pass


def body_hash(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class HttpTransport:
    """POSTs to the Messages API with the standard library only."""

    def __init__(self, url: str = API_URL, timeout: float = 60.0):
        self.url, self.timeout = url, timeout
        self.calls = 0

    def __repr__(self) -> str:   # no headers, no key
        return f"HttpTransport(url={self.url!r}, calls={self.calls})"

    def __call__(self, body: dict) -> dict:
        key = os.environ.get(KEY_ENV, "").strip()
        if not key:
            raise MissingKey(f"{KEY_ENV} is not set")
        req = urllib.request.Request(
            self.url, data=json.dumps(body).encode(), method="POST",
            headers={"content-type": "application/json",
                     "anthropic-version": api_version(),
                     "x-api-key": key})
        del key
        self.calls += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail)["error"]["message"]
            except (ValueError, KeyError, TypeError):
                pass
            raise APIError(exc.code, detail) from None


class FixtureTransport:
    """Replays responses recorded by ModelClient(record_dir=...)."""

    def __init__(self, directory: Path):
        self.by_hash = {}
        for path in sorted(Path(directory).glob("*.json")):
            rec = json.loads(path.read_text())
            self.by_hash[rec["request_hash"]] = rec["response"]
        self.calls = 0

    def __call__(self, body: dict) -> dict:
        self.calls += 1
        h = body_hash(body)
        if h not in self.by_hash:
            raise NoFixture(f"no recorded response for request {h}")
        return self.by_hash[h]


@dataclass
class Completion:
    text: str
    model: str
    pinned: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cached: bool
    stop_reason: str | None
    request_hash: str

    @property
    def drifted(self) -> bool:
        """True when the provider answered with a model other than the pin."""
        return self.model != self.pinned


class ModelClient:
    def __init__(self, model: str = "small",
                 meter: SpendMeter | None = None,
                 transport: Transport | None = None,
                 cache_dir: Path | None = None,
                 record_dir: Path | None = None):
        self.pin: ModelPin = pin(model)
        self.meter = meter if meter is not None else SpendMeter()
        self.transport = transport if transport is not None \
            else HttpTransport()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.record_dir = Path(record_dir) if record_dir else None

    def __repr__(self) -> str:
        return (f"ModelClient(model={self.pin.id!r}, "
                f"spent=${self.meter.spent_usd:.4f})")

    def request_body(self, prompt: str, system: str | None,
                     max_tokens: int, temperature: float | None) -> dict:
        body = {"model": self.pin.id, "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}]}
        if system:
            body["system"] = system
        if temperature is not None:
            body["temperature"] = temperature
        return body

    def complete(self, prompt: str, system: str | None = None,
                 max_tokens: int = 64,
                 temperature: float | None = None) -> Completion:
        body = self.request_body(prompt, system, max_tokens, temperature)
        h = body_hash(body)
        cached = self._read(self.cache_dir, h)
        if cached is not None:
            return self._completion(cached, h, cost=0.0, was_cached=True)
        self.meter.check(self.pin, len(prompt) + len(system or ""),
                         max_tokens)
        resp = self.transport(body)
        cost = self.meter.record(self.pin, resp.get("usage", {}))
        for d in (self.cache_dir, self.record_dir):
            self._write(d, h, body, resp)
        return self._completion(resp, h, cost, was_cached=False)

    def _completion(self, resp: dict, h: str, cost: float,
                    was_cached: bool) -> Completion:
        text = "".join(b.get("text", "") for b in resp.get("content", [])
                       if b.get("type") == "text")
        usage = resp.get("usage", {})
        return Completion(text=text, model=resp.get("model", ""),
                          pinned=self.pin.id,
                          input_tokens=usage.get("input_tokens", 0),
                          output_tokens=usage.get("output_tokens", 0),
                          cost_usd=cost, cached=was_cached,
                          stop_reason=resp.get("stop_reason"),
                          request_hash=h)

    def _read(self, d: Path | None, h: str) -> dict | None:
        if d is None:
            return None
        path = d / f"{h}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())["response"]

    def _write(self, d: Path | None, h: str, body: dict,
               resp: dict) -> None:
        if d is None:
            return
        d.mkdir(parents=True, exist_ok=True)
        rec = redact({"request_hash": h, "request": body,
                      "response": resp})
        (d / f"{h}.json").write_text(
            json.dumps(rec, indent=2, sort_keys=True) + "\n")
