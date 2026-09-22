# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Infisical ConfigStore Adapter."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from vibey.application.interfaces.config_store import ConfigStorePort


class InfisicalConfigStoreAdapter(ConfigStorePort):
    def __init__(
        self,
        *,
        url: str,
        token: str,
        project_id: str,
        environment: str = "dev",
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self._url = url.strip().rstrip("/")
        self._token = token
        self._project_id = project_id
        self._environment = environment
        self._opener = opener

    async def create_config(self, key: str, value: str) -> None:
        await asyncio.to_thread(self._create_config_sync, key, value)

    def _create_config_sync(self, key: str, value: str) -> None:
        url = f"{self._url}/api/v4/secrets/{urllib.parse.quote(key)}"
        payload = {
            "projectId": self._project_id,
            "environment": self._environment,
            "secretValue": value,
            "secretPath": "/",
            "type": "shared",
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener(req) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            raise RuntimeError(f"Infisical API error: {exc.code} - {body}") from exc

    async def get_config(self, key: str) -> str:
        return await asyncio.to_thread(self._get_config_sync, key)

    def _get_config_sync(self, key: str) -> str:
        params = urllib.parse.urlencode(
            {
                "projectId": self._project_id,
                "environment": self._environment,
                "secretPath": "/",
            }
        )
        url = f"{self._url}/api/v4/secrets/{urllib.parse.quote(key)}?{params}"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._token}"},
            method="GET",
        )
        try:
            with self._opener(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return str(data["secret"]["secretValue"])
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise KeyError(f"Config key not found in Infisical: {key}") from exc
            try:
                body = exc.read().decode("utf-8")
            except Exception:
                body = ""
            raise RuntimeError(f"Infisical API error: {exc.code} - {body}") from exc
