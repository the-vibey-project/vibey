# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One S3 Signature Version 4 signer for the family (ADR-0105 OR-3; sub-doctrine 10.e).

Extracted from `GarageBlobAdapter`, which signed its own requests, so the run input store's
SeaweedFS backend reuses it rather than carrying a second implementation. Stdlib only: the
HMAC-SHA256 chain over the canonical request, as AWS documents it. The secret is held for
signing only: the class has no `__repr__` that shows it, and it is never put in a header.

Declared by `interfaces/s3_request_signer_interface.py::S3RequestSignerInterface`.
"""

from __future__ import annotations

import hashlib
import hmac
import urllib.parse
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Final

SERVICE: Final = "s3"
ALGORITHM: Final = "AWS4-HMAC-SHA256"
_UNRESERVED: Final = "-_.~"


class S3RequestSigner:
    """Declared by `interfaces/s3_request_signer_interface.py`."""

    __slots__ = ("_access_key", "_clock", "_region", "_secret_key")

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        region: str,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._clock = clock

    def __repr__(self) -> str:
        return f"S3RequestSigner(access_key={self._access_key!r}, region={self._region!r})"

    @property
    def access_key(self) -> str:
        return self._access_key

    def canonical_query(self, query: Mapping[str, str]) -> str:
        return "&".join(
            f"{urllib.parse.quote(key, safe=_UNRESERVED)}="
            f"{urllib.parse.quote(value, safe=_UNRESERVED)}"
            for key, value in sorted(query.items())
        )

    def headers(
        self,
        *,
        method: str,
        host: str,
        canonical_uri: str,
        query: Mapping[str, str],
        body: bytes,
        signed: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        payload_hash = hashlib.sha256(body).hexdigest()
        now = self._clock().astimezone(UTC)
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        datestamp = now.strftime("%Y%m%d")
        headers = {name.lower(): value for name, value in (signed or {}).items()}
        headers.update({"host": host, "x-amz-content-sha256": payload_hash, "x-amz-date": amz_date})
        names = sorted(headers)
        canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in names)
        canonical = "\n".join(
            [
                method,
                canonical_uri,
                self.canonical_query(query),
                canonical_headers,
                ";".join(names),
                payload_hash,
            ]
        )
        scope = f"{datestamp}/{self._region}/{SERVICE}/aws4_request"
        string_to_sign = "\n".join(
            [ALGORITHM, amz_date, scope, hashlib.sha256(canonical.encode()).hexdigest()]
        )
        headers["Authorization"] = (
            f"{ALGORITHM} Credential={self._access_key}/{scope}, "
            f"SignedHeaders={';'.join(names)}, Signature={self._signature(datestamp, string_to_sign)}"
        )
        return headers

    def _signature(self, datestamp: str, string_to_sign: str) -> str:
        key = f"AWS4{self._secret_key}".encode()
        for part in (datestamp, self._region, SERVICE, "aws4_request"):
            key = hmac.new(key, part.encode(), hashlib.sha256).digest()
        return hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()
