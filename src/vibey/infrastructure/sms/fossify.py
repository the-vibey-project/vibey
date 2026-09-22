# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fossify SMS Adapter implementation."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from vibey.application.interfaces.sms import SmsPort


class FossifySmsAdapter(SmsPort):
    def __init__(self, url: str, token: str | None = None) -> None:
        self.url = url
        self.token = token

    async def send_sms(self, phone_number: str, message: str) -> None:
        payload = {"phone_number": phone_number, "message": message}
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(self.url, data=data, headers=headers, method="POST")

        def _send() -> None:
            with urllib.request.urlopen(req) as resp:  # nosec B310 - https-only endpoints are config
                resp.read()

        await asyncio.to_thread(_send)
