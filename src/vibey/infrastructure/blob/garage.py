# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Garage Blob adapter implementing the Blob storage port (ADR-0042).

Self-hosted Garage over its S3-compatible API with stdlib only. S3 signs
every request with Signature Version 4 (HMAC-SHA256 chain over the canonical
request) -- implemented here rather than pulled in, because the port needs
four calls and a client library would be a heavier dependency than the
 eighty lines the signature takes.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from typing import Any

from vibey.application.interfaces.blob import BlobPort

_SERVICE = "s3"
_ALGORITHM = "AWS4-HMAC-SHA256"


def _hmac(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _signature(
    *,
    secret_key: str,
    region: str,
    datestamp: str,
    string_to_sign: str,
) -> str:
    scope_date = _hmac(f"AWS4{secret_key}".encode(), datestamp)
    scope_region = hmac.new(scope_date, region.encode(), hashlib.sha256).digest()
    scope_service = hmac.new(scope_region, _SERVICE.encode(), hashlib.sha256).digest()
    signing = hmac.new(scope_service, b"aws4_request", hashlib.sha256).digest()
    return hmac.new(signing, string_to_sign.encode(), hashlib.sha256).hexdigest()


def _canonical_uri(bucket: str, key: str) -> str:
    parts = [urllib.parse.quote(bucket, safe="")]
    if key:
        parts.extend(urllib.parse.quote(part, safe="") for part in key.split("/"))
    return "/" + "/".join(parts)


class GarageBlobAdapter(BlobPort):
    def __init__(
        self,
        *,
        url: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
        opener: Any = urllib.request.urlopen,
    ) -> None:
        self._url = url.strip().rstrip("/")
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._opener = opener
        self._host = urllib.parse.urlsplit(self._url).netloc

    def _signed_request(
        self,
        method: str,
        uri: str,
        body: bytes | None,
        content_type: str | None,
    ) -> urllib.request.Request:
        payload_hash = hashlib.sha256(body or b"").hexdigest()
        now = datetime.now(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")
        headers = {
            "host": self._host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if content_type is not None:
            headers["content-type"] = content_type
        names = sorted(headers)
        canonical_headers = "".join(f"{name}:{headers[name]}\n" for name in names)
        canonical = "\n".join([method, uri, "", canonical_headers, ";".join(names), payload_hash])
        scope = f"{datestamp}/{self._region}/{_SERVICE}/aws4_request"
        string_to_sign = "\n".join(
            [_ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()]
        )
        signature = _signature(
            secret_key=self._secret_key,
            region=self._region,
            datestamp=datestamp,
            string_to_sign=string_to_sign,
        )
        headers["Authorization"] = (
            f"{_ALGORITHM} Credential={self._access_key}/{scope}, "
            f"SignedHeaders={';'.join(names)}, Signature={signature}"
        )
        return urllib.request.Request(  # nosec B310 - https-only endpoints are config
            f"{self._url}{uri}", data=body, headers=headers, method=method
        )

    def _send(self, req: urllib.request.Request) -> tuple[int, bytes]:
        try:
            with self._opener(req) as resp:
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
