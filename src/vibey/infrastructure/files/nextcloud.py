# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Nextcloud WebDAV adapter implementing the File manager port (ADR-0042).

Self-hosted Nextcloud over stdlib urllib; upload returns the public WebDAV URL.
"""

from __future__ import annotations

import asyncio
import base64
import urllib.error
import urllib.parse
import urllib.request

from vibey.application.interfaces.files import FilesPort


class NextcloudFilesAdapter(FilesPort):
    def __init__(self, *, url: str, user: str, password: str, opener: object | None = None) -> None:
        self._url = url.rstrip("/")
        self._user = user
        self._password = password
        self._opener = opener if opener is not None else urllib.request.urlopen

    def _dav_url(self, remote_path: str) -> str:
        # Quote each segment so spaces, `#` and other reserved characters
        # survive as data; `/` separators are preserved by quoting per part.
        encoded = "/".join(
            urllib.parse.quote(part, safe="") for part in remote_path.lstrip("/").split("/")
        )
        user = urllib.parse.quote(self._user, safe="")
        return f"{self._url}/remote.php/dav/files/{user}/{encoded}"

    def _headers(self) -> dict[str, str]:
        credentials = base64.b64encode(f"{self._user}:{self._password}".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}

    async def upload_file(self, remote_path: str, content: bytes) -> str:
        return await asyncio.to_thread(self._upload_sync, remote_path, content)

    def _upload_sync(self, remote_path: str, content: bytes) -> str:
        dav_url = self._dav_url(remote_path)
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            dav_url, data=content, headers=self._headers(), method="PUT"
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                resp.read()
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Nextcloud API error {exc.code}: {exc.reason}") from exc
        return dav_url

    async def download_file(self, remote_path: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, remote_path)

    def _download_sync(self, remote_path: str) -> bytes:
        req = urllib.request.Request(  # nosec B310 - https-only endpoints are config
            self._dav_url(remote_path), headers=self._headers(), method="GET"
        )
        try:
            with self._opener(req) as resp:  # type: ignore[operator]
                data = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise FileNotFoundError(remote_path) from exc
            raise RuntimeError(f"Nextcloud API error {exc.code}: {exc.reason}") from exc
        return bytes(data)
