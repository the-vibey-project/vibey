# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Matrix/Element adapter implementing the Instant Messenger port (ADR-0042).

Self-hosted Matrix over stdlib urllib; sovereign default for instant messaging.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from vibey.application.interfaces.messaging import MessagingPort


class MatrixMessagingAdapter(MessagingPort):
    def __init__(self, *, url: str, token: str, opener: object | None = None) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._opener = opener if opener is not None else urllib.request.urlopen

    async def send_message(self, channel_id: str, message: str) -> None:
        await asyncio.to_thread(self._send_sync, channel_id, message)

    def _send_sync(self, channel_id: str, message: str) -> None:
        payload = json.dumps({"msgtype": "m.text", "body": message}).encode("utf-8")
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/_matrix/client/v3/rooms/{channel_id}/send/m.room.message/"
            f"vibey-{abs(hash(message))}",
            data=payload,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="PUT",
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Matrix API error {exc.code}: {exc.reason}") from exc
