# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ management HTTP API, spoken with stdlib urllib only (ADR-0042).

One client for everything vibey says to the management plugin: the bus adapter's
declare, publish and get, and the reaper's measurements and policy (ADR-0056). No AMQP
client is involved; the management API is a diagnostics surface, which is why the bus
adapter over it is at-most-once and why the job queue's transport (ADR-0044) is not it.
"""

from __future__ import annotations

import base64
import http.client
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


class RabbitMqUnreachable(RuntimeError):
    """The management API could not be reached at all: no answer, not an HTTP error. The
    message names the kind of failure and never the URL's credentials (#1108 review)."""


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
        parsed = urllib.parse.urlsplit(url.strip())
        if parsed.username is not None or parsed.password is not None or "@" in parsed.netloc:
            # A credential in the URL is logged with every error the URL appears in, and
            # urllib reads `user:pw@host` with no port as a host whose port is `pw@host`.
            # The credentials have their own keys, sent as a header, never as text.
            raise ValueError(
                "the RabbitMQ management URL must not carry credentials; set [bus] "
                "username and password (VIBEY_BUS_USERNAME, VIBEY_BUS_PASSWORD) instead"
            )
        self._url = url.strip().rstrip("/")
        self._password = password
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
            raise RabbitMqApiError(exc.code, self._scrubbed(str(exc.reason))) from None
        except (OSError, ValueError, http.client.HTTPException) as exc:
            # `from None`: the original exception's text can quote the URL.
            raise RabbitMqUnreachable(
                f"cannot reach the RabbitMQ management API: {type(exc).__name__}: "
                f"{self._scrubbed(str(exc))}"
            ) from None
        return json.loads(raw) if raw.strip() else None

    def _scrubbed(self, text: str) -> str:
        """`text` with the password replaced, whatever quoted it. The username is not a
        secret, and replacing it would mangle every host named after it."""
        return text.replace(self._password, "***") if self._password else text
