# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The S3 SigV4 signing seam (ADR-0105 OR-3).

Mirrors `vibey/infrastructure/blob/s3_request_signer.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class S3RequestSignerInterface(Protocol):
    """Signs one S3 request with Signature Version 4 for one access key, secret and region."""

    @property
    def access_key(self) -> str:
        """The access key id the signature names (not a secret: it is in every request)."""
        ...

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
        """The headers that sign the request: `host`, `x-amz-content-sha256`, `x-amz-date`,
        every header of `signed` (lower-cased, signed with them), and `Authorization`.

        `canonical_uri` is already percent-encoded (`/bucket/key`); `query` is unencoded and is
        encoded here exactly as the request must send it (`canonical_query`)."""
        ...

    def canonical_query(self, query: Mapping[str, str]) -> str:
        """`query` as SigV4 canonicalizes it: sorted by key, each key and value
        percent-encoded with only `A-Z a-z 0-9 - _ . ~` left as they are. Send the request with
        this exact string so what is signed is what is sent."""
        ...
