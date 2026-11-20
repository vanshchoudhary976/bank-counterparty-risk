"""Stand-ins for the HTTP session so tests never touch the network."""

from __future__ import annotations

import json
from typing import Any


class FakeResponse:
    def __init__(self, body: Any = None, status: int = 200, content: bytes | None = None) -> None:
        self._body = body
        self.status_code = status
        self.content = content if content is not None else json.dumps(body).encode("utf-8")

    def json(self) -> Any:
        return self._body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Returns queued responses in order and records every request it receives."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def get(self, url: str, params: dict | None = None, headers: dict | None = None, timeout: float | None = None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        if not self.responses:
            raise AssertionError("FakeSession ran out of queued responses")
        return self.responses.pop(0)
