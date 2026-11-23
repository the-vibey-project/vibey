# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An in-memory S3 behind `httpx.MockTransport`, for the SeaweedFS input store's tests (SP-LOOPS
Phase 3c). There is no SeaweedFS and no network: every request is answered here.

It checks every request's SigV4 signature by signing the request it received again with the
family's signer, so a store that sent something other than what it signed fails here. It speaks
the subset the store uses: ListObjectsV2 (paged, with continuation tokens), HEAD, GET and PUT of
an object, and the S3 error bodies `NoSuchBucket` and `NoSuchKey`. `answer` lets a test replace
the answer to any request. Test support, not production code (ADR-0016 is about production code).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from urllib.parse import parse_qsl, quote, unquote
from xml.sax.saxutils import escape

import httpx

from vibey.infrastructure.blob.s3_request_signer import S3RequestSigner

ENDPOINT = "https://files.example.test:8333"
BUCKET = "vibey-inputs"
ACCESS = "FAKEACCESS"
SECRET = "fake-secret-sentinel-9f3c"
REGION = "us-east-1"


def _error(status: int, code: str) -> httpx.Response:
    return httpx.Response(status, content=f"<Error><Code>{code}</Code></Error>".encode())


class FakeS3:
    """The bucket's objects, every request seen, and an optional override of any answer."""

    def __init__(
        self,
        *,
        buckets: tuple[str, ...] = (BUCKET,),
        page_size: int = 1000,
        secret: str = SECRET,
    ) -> None:
        self.buckets = set(buckets)
        self.objects: dict[str, bytes] = {}
        self.requests: list[httpx.Request] = []
        self.page_size = page_size
        self.answer: Callable[[httpx.Request], httpx.Response | None] = lambda request: None
        self._secret = secret

    def client(self, **kwargs: object) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(self.handle),
            follow_redirects=False,
            **kwargs,  # type: ignore[arg-type]
        )

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if not self._signature_matches(request):
            return _error(403, "SignatureDoesNotMatch")
        override = self.answer(request)
        if override is not None:
            return override
        path = unquote(request.url.raw_path.decode().split("?", 1)[0])
        bucket, _, key = path.lstrip("/").partition("/")
        if not key:
            if request.method == "PUT":
                self.buckets.add(bucket)
                return httpx.Response(200)
            if bucket not in self.buckets:
                return _error(404, "NoSuchBucket")
            return self._list(dict(parse_qsl(request.url.query.decode())))
        if bucket not in self.buckets:
            return _error(404, "NoSuchBucket")
        if request.method == "PUT":
            self.objects[key] = request.read()
            return httpx.Response(200)
        if key not in self.objects:
            return httpx.Response(404) if request.method == "HEAD" else _error(404, "NoSuchKey")
        data = self.objects[key]
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(data))})
        return httpx.Response(200, content=data)

    def _list(self, query: dict[str, str]) -> httpx.Response:
        assert query.get("list-type") == "2"
        prefix = query.get("prefix", "")
        keys = sorted(key for key in self.objects if key.startswith(prefix))
        start = int(query.get("continuation-token", "tok-0").removeprefix("tok-"))
        size = min(self.page_size, int(query.get("max-keys", "1000")))
        page = keys[start : start + size]
        truncated = start + size < len(keys)
        contents = "".join(f"<Contents><Key>{escape(key)}</Key></Contents>" for key in page)
        token = f"<NextContinuationToken>tok-{start + size}</NextContinuationToken>"
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f"<Name>{BUCKET}</Name><Prefix>{escape(prefix)}</Prefix>"
            f"<IsTruncated>{'true' if truncated else 'false'}</IsTruncated>"
            f"{contents}{token if truncated else ''}</ListBucketResult>"
        )
        return httpx.Response(200, content=body.encode())

    def _signature_matches(self, request: httpx.Request) -> bool:
        """Signs the request again as S3 does: over the DECODED key re-encoded strictly (so a
        store that signs one string and sends another fails here, as it would there), the query
        as sent, and the body. A mismatch is S3's 403 `SignatureDoesNotMatch`."""
        when = datetime.strptime(request.headers["x-amz-date"], "%Y%m%dT%H%M%SZ").replace(
            tzinfo=UTC
        )
        signer = S3RequestSigner(ACCESS, self._secret, REGION, clock=lambda: when)
        decoded = unquote(request.url.raw_path.decode().split("?", 1)[0])
        canonical_uri = "/".join(quote(segment, safe="-_.~") for segment in decoded.split("/"))
        query = dict(parse_qsl(request.url.query.decode(), keep_blank_values=True))
        if signer.canonical_query(query) != request.url.query.decode():
            return False
        expected = signer.headers(
            method=request.method,
            host=request.url.netloc.decode(),
            canonical_uri=canonical_uri,
            query=query,
            body=request.read(),
        )
        return request.headers.get("authorization") == expected["Authorization"]
