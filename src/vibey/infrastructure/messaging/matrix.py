# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Matrix/Element adapter implementing the Instant Messenger port (ADR-0042).

Self-hosted Matrix over stdlib urllib; sovereign default for instant messaging.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
import uuid

from vibey.application.interfaces.messaging import MessagingPort
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS


class MatrixMessagingAdapter(MessagingPort):
    def __init__(
        self,
        *,
        url: str,
        token: str,
        opener: object | None = None,
        timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS,
    ) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._opener = opener if opener is not None else urllib.request.urlopen
        self._timeout = timeout

    async def send_message(self, channel_id: str, message: str) -> None:
        await asyncio.to_thread(self._send_sync, channel_id, message)

    def _send_sync(self, channel_id: str, message: str) -> None:
        payload = json.dumps({"msgtype": "m.text", "body": message}).encode("utf-8")
        # The transaction ID must be unique per send: deriving it from the
        # message text reuses one ID for a repeated message, and Matrix treats
        # the second PUT as the first request's idempotent retry -- the second
        # notification is silently dropped.
        txn_id = f"vibey-{uuid.uuid4()}"
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/_matrix/client/v3/rooms/{channel_id}/send/m.room.message/{txn_id}",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with self._opener(req, timeout=self._timeout) as resp:  # type: ignore[operator]
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Matrix API error {exc.code}: {exc.reason}") from exc
