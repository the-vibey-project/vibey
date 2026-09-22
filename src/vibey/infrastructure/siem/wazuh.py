# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Wazuh SIEM adapter implementing the SIEM port (ADR-0042).

Self-hosted Wazuh over its indexer's document API with stdlib urllib only.
Audit events land directly in the named index, where the manager's rules and
the dashboard can correlate them; no agent install, no syslog surgery. The
indexer auto-creates an index on first write.
"""

from __future__ import annotations

import asyncio
import base64
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from vibey.application.interfaces.siem import SiemPort


class WazuhSiemAdapter(SiemPort):
    def __init__(
        self,
        *,
        url: str,
        username: str | None = None,
        password: str | None = None,
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self._url = url.strip().rstrip("/")
        self._auth: dict[str, str] = {}
        if username is not None and password is not None:
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            self._auth = {"Authorization": f"Basic {credentials}"}
        self._opener = opener

    async def send_event(self, index: str, event: dict[str, object]) -> None:
        await asyncio.to_thread(self._send_sync, index, event)

    def _send_sync(self, index: str, event: dict[str, object]) -> None:
        document = {"timestamp": datetime.now(UTC).isoformat(), **event}
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/{index}/_doc",
            data=json.dumps(document).encode("utf-8"),
            headers={**self._auth, "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(req) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"SIEM index failed: HTTP {exc.code}") from exc
