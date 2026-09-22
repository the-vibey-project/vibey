# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""OpenBao Secrets adapter implementing the Secrets port (ADR-0042).

Self-hosted OpenBao (MPL-licensed Vault fork) over its KV version 2 HTTP API
with stdlib urllib only. Static token auth, one JSON object per key.

Why not Bitwarden here: Bitwarden Secrets Manager has no self-hostable
single-container form, and Vaultwarden (its self-hostable sibling) keeps
vault crypto client-side -- AES decryption is not stdlib, so no honest
urllib-only adapter can read it. OpenBao is the FOSS secrets server whose
API this port can actually speak.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from vibey.application.interfaces.secrets import SecretsPort


class OpenBaoSecretsAdapter(SecretsPort):
    def __init__(self, *, url: str, token: str, opener: Any = urllib.request.urlopen) -> None:
        self._url = url.strip().rstrip("/")
        self._token = token
        self._opener = opener

    def _headers(self) -> dict[str, str]:
        return {"X-Vault-Token": self._token, "Content-Type": "application/json"}

    def _key_url(self, key: str) -> str:
        encoded = "/".join(urllib.parse.quote(part, safe="") for part in key.split("/"))
        return f"{self._url}/v1/secret/data/{encoded}"

    async def get_secret(self, key: str) -> str:
        return await asyncio.to_thread(self._get_sync, key)

    def _get_sync(self, key: str) -> str:
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            self._key_url(key), headers=self._headers(), method="GET"
        )
        try:
            with self._opener(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise KeyError(f"secret {key!r} not found") from exc
            raise RuntimeError(f"OpenBao API error {exc.code}: {exc.reason}") from exc
        try:
            return str(data["data"]["data"]["value"])
        except (KeyError, TypeError) as exc:
            raise RuntimeError(f"OpenBao returned no value for {key!r}") from exc

    async def set_secret(self, key: str, value: str) -> None:
        await asyncio.to_thread(self._set_sync, key, value)

    def _set_sync(self, key: str, value: str) -> None:
        payload = json.dumps({"data": {"value": value}}).encode("utf-8")
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            self._key_url(key),
            data=payload,
            headers=self._headers(),
            method="PUT",
        )
        try:
            with self._opener(req) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenBao API error {exc.code}: {exc.reason}") from exc
