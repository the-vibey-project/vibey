# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Bitwarden Secrets Manager adapter implementing the Secrets port (ADR-0042).

Self-hosted Bitwarden (or the sovereign Secrets Manager API) over stdlib urllib.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from vibey.application.interfaces.secrets import SecretsPort


class BitwardenSecretsAdapter(SecretsPort):
    def __init__(self, *, url: str, token: str, opener: object | None = None) -> None:
        self._url = url.rstrip("/")
        self._token = token
        self._opener = opener if opener is not None else urllib.request.urlopen

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def get_secret(self, key: str) -> str:
        return await asyncio.to_thread(self._get_sync, key)

    def _get_sync(self, key: str) -> str:
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/api/secrets/{key}", headers=self._headers(), method="GET"
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise KeyError(f"secret {key!r} not found") from exc
            raise RuntimeError(f"Bitwarden API error {exc.code}: {exc.reason}") from exc
        return str(data["value"])

    async def set_secret(self, key: str, value: str) -> None:
        await asyncio.to_thread(self._set_sync, key, value)

    def _set_sync(self, key: str, value: str) -> None:
        payload = json.dumps({"value": value}).encode("utf-8")
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/api/secrets/{key}",
            data=payload,
            headers=self._headers(),
            method="POST",
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Bitwarden API error {exc.code}: {exc.reason}") from exc
