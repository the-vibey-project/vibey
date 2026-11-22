# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a fake SearXNG answers in tests: its `/config` identity, and responses that say where
they landed. Every key used beside them is a fake."""

from __future__ import annotations

import json
import urllib.request

SEARXNG_CONFIG: dict[str, object] = {
    "categories": ["general", "it"],
    "engines": [{"name": "duckduckgo", "categories": ["general"], "enabled": True}],
    "plugins": [],
    "instance_name": "SearXNG",
    "locales": {"en": "English"},
    "version": "2025.11.1+abc123",
    "brand": {},
    "limiter": {"enabled": False},
    "doi_resolvers": [],
}
"""What a real SearXNG's `/config` answers (the keys `searx/webapp.py` returns), trimmed."""


class FakeResponse:
    def __init__(self, payload: object, url: str | None = None) -> None:
        self._payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.url = url
        self.asked: list[int | None] = []

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self, amount: int | None = None) -> bytes:
        self.asked.append(amount)
        return self._payload


def is_config(request: urllib.request.Request) -> bool:
    return request.full_url.split("?", 1)[0].endswith("/config")
