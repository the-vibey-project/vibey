# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ management HTTP API, spoken with stdlib urllib only (ADR-0042).

One client for everything vibey says to the management plugin: the bus adapter's
declare, publish and get, and the reaper's measurements and policy (ADR-0056). No AMQP
client is involved; the management API is a diagnostics surface, which is why the bus
adapter over it is at-most-once and why the job queue's transport (ADR-0044) is not it.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class RabbitMqApiError(RuntimeError):
    """The management API answered with an HTTP error. `status` is its code."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(f"RabbitMQ API error {status}: {reason}")
        self.status = status


class RabbitMqManagementApi:
    """Authenticated requests to one broker's management API, scoped to one vhost."""

    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        vhost: str = "/",
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self._url = url.strip().rstrip("/")
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._auth = {"Authorization": f"Basic {credentials}"}
        self.vhost = urllib.parse.quote(vhost, safe="")
        """The vhost, percent-encoded for a path segment."""
        self._opener = opener

    def name(self, value: str) -> str:
        """A queue, exchange or policy name, percent-encoded for a path segment."""
        return urllib.parse.quote(value, safe="")

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Any:
        """One call; the decoded JSON, or None for an empty body. An HTTP error is a
        `RabbitMqApiError` naming the status, never a silent None."""
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = dict(self._auth)
        if body is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/api/{path}", data=body, headers=headers, method=method
        )
        try:
            with self._opener(req) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RabbitMqApiError(exc.code, str(exc.reason)) from exc
        return json.loads(raw) if raw.strip() else None
