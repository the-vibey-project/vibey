# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""BookStack Docs adapter implementing the Documentation port (ADR-0042).

Self-hosted BookStack over its token-authenticated JSON API; stdlib urllib only.
"""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from vibey.application.interfaces.docs import DocsPort


class BookStackDocsAdapter(DocsPort):
    def __init__(
        self,
        *,
        url: str,
        token_id: str,
        token_secret: str,
        book_id: int = 1,
        opener: object | None = None,
    ) -> None:
        self._url = url.rstrip("/")
        self._token_id = token_id
        self._token_secret = token_secret
        self._book_id = book_id
        self._opener = opener if opener is not None else urllib.request.urlopen

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self._token_id}:{self._token_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def create_page(self, title: str, content: str) -> str:
        return await asyncio.to_thread(self._create_sync, title, content)

    def _create_sync(self, title: str, content: str) -> str:
        payload = json.dumps({"title": title, "content": content, "book_id": self._book_id}).encode(
            "utf-8"
        )
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/api/pages", data=payload, headers=self._headers(), method="POST"
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"BookStack API error {exc.code}: {exc.reason}") from exc
        return str(data["id"])

    async def update_page(self, page_id: str, content: str) -> None:
        await asyncio.to_thread(self._update_sync, page_id, content)

    def _update_sync(self, page_id: str, content: str) -> None:
        existing_title = f"page {page_id}"
        payload = json.dumps(
            {"title": existing_title, "content": content, "book_id": self._book_id}
        ).encode("utf-8")
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}/api/pages/{page_id}",
            data=payload,
            headers=self._headers(),
            method="PUT",
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"BookStack API error {exc.code}: {exc.reason}") from exc
