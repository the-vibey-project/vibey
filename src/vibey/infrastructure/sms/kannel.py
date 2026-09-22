# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Kannel SMS adapter implementing the SMS port (ADR-0042).

Self-hosted Kannel over its smsbox sendsms CGI with stdlib urllib only:
`GET /cgi-bin/sendsms?username=&password=&from=&to=&text=`. A `0:`-prefixed
body means accepted; anything else (including HTTP errors) raises. The
user-facing default on handsets stays Fossify Messages; Kannel is the
gateway that puts the bytes on the air.
"""

from __future__ import annotations

import asyncio
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from vibey.application.interfaces.sms import SmsPort


class KannelSmsAdapter(SmsPort):
    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        sender: str = "vibey",
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self._url = url.strip().rstrip("/")
        self._username = username
        self._password = password
        self._sender = sender
        self._opener = opener

    async def send_sms(self, phone_number: str, message: str) -> None:
        await asyncio.to_thread(self._send_sync, phone_number, message)

    def _send_sync(self, phone_number: str, message: str) -> None:
        query = urllib.parse.urlencode(
            {
                "username": self._username,
                "password": self._password,
                "from": self._sender,
                "to": phone_number,
                "text": message,
            }
        )
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/cgi-bin/sendsms?{query}", method="GET"
        )
        try:
            with self._opener(req) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Kannel sendsms failed: HTTP {exc.code}") from exc
        if not body.startswith("0:"):
            raise RuntimeError(f"Kannel rejected the message: {body.strip()[:200]}")
