# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Garage Blob adapter implementing the Blob storage port (ADR-0042).

Self-hosted Garage over its S3-compatible API with stdlib only. Every request is signed with
Signature Version 4 by the family's one signer, `S3RequestSigner` (extracted from this module so
the run input store reuses it; ADR-0105 OR-3, sub-doctrine 10.e).
"""

from __future__ import annotations

import asyncio
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from vibey.application.interfaces.blob import BlobPort
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.blob.s3_request_signer import S3RequestSigner


def _canonical_uri(bucket: str, key: str) -> str:
    parts = [urllib.parse.quote(bucket, safe="")]
    if key:
        parts.extend(urllib.parse.quote(part, safe="") for part in key.split("/"))
    return "/" + "/".join(parts)


def _now() -> datetime:
    """The signing clock, read through this module's `datetime` so a test can fix it."""
    return datetime.now(UTC)


class GarageBlobAdapter(BlobPort):
    def __init__(
        self,
        *,
        url: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        opener: Any = urllib.request.urlopen,
        timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._url = url.strip().rstrip("/")
        self._opener = opener
        self._timeout = timeout
        self._host = urllib.parse.urlsplit(self._url).netloc
        self._signer = S3RequestSigner(access_key, secret_key, region, clock=_now)

    def _signed_request(
        self,
        method: str,
        uri: str,
        body: bytes | None,
        content_type: str | None,
    ) -> urllib.request.Request:
        headers = self._signer.headers(
            method=method,
            host=self._host,
            canonical_uri=uri,
            query={},
            body=body or b"",
            signed=None if content_type is None else {"content-type": content_type},
        )
        return urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}{uri}", data=body, headers=headers, method=method
        )

    def _send(self, req: urllib.request.Request) -> tuple[int, bytes]:
        try:
            with self._opener(req, timeout=self._timeout) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read()
            except Exception:
                body = b""
            return exc.code, body

    @staticmethod
    def _error_code(body: bytes) -> str:
        match = re.search(rb"<Code>([^<]+)</Code>", body)
        return match.group(1).decode("utf-8", "replace") if match else ""

    async def put_blob(
        self, bucket: str, key: str, content: bytes, content_type: str | None = None
    ) -> str:
        return await asyncio.to_thread(self._put_sync, bucket, key, bytes(content), content_type)

    def _put_sync(self, bucket: str, key: str, content: bytes, content_type: str | None) -> str:
        status, body = self._send(
            self._signed_request("PUT", _canonical_uri(bucket, ""), None, None)
        )
        if status not in (200, 409) or (
            status == 409
            and self._error_code(body) not in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists")
        ):
            raise RuntimeError(f"blob bucket create failed: HTTP {status}")
        uri = _canonical_uri(bucket, key)
        status, _ = self._send(
            self._signed_request("PUT", uri, content, content_type or "application/octet-stream")
        )
        if status != 200:
            raise RuntimeError(f"blob put failed: HTTP {status}")
        return f"{self._url}{uri}"

    async def get_blob(self, bucket: str, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, bucket, key)

    def _get_sync(self, bucket: str, key: str) -> bytes:
        status, body = self._send(
            self._signed_request("GET", _canonical_uri(bucket, key), None, None)
        )
        if status == 200:
            return bytes(body)
        if status == 404 or self._error_code(body) in ("NoSuchKey", "NoSuchBucket"):
            raise FileNotFoundError(f"blob {bucket}/{key} not found")
        raise RuntimeError(f"blob get failed: HTTP {status}")
