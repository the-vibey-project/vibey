# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The person's run inputs in a SeaweedFS bucket, over the S3 API (SP-LOOPS Phase 3c, Task 4;
ADR-0105). Opt-in with `[inputs] store = "seaweedfs"`; the local store stays the default.

**Where.** Path-style requests to the endpoint the person named, `<endpoint>/<bucket>/<key>`, and
nowhere else: the client follows no redirect. Every request is signed with SigV4 by the family's
one signer (`S3RequestSigner`, ADR-0105 OR-3), with the credentials read from the two environment
variables `[inputs]` names. The bucket is never created: least authority means the credentials
may be scoped to one bucket, and a missing bucket is an error that says so.

**Layout.** Under `<prefix>/<project id>/`: `objects/<digest[:2]>/<digest>` holds each input's
bytes once, and, since S3 has no append, each index row is its own object,
`index/<ns:020d>-<uuid hex>.json`. ListObjectsV2 returns keys in order, so the listing is the
add order; two adds in one nanosecond are ordered by their uuids.

**Writing.** `put` first asks whether an object with that digest is already there and intact
(HEAD for its size, then GET and compare the digest) and writes it only when it is not; then it
writes the row. The object comes first, so a failure leaves at most an object no row names.

**Reading.** `get` refuses an object whose `Content-Length` is not its row's size before reading
the body, reads at most `size + 1` bytes, and checks the digest. `listed` pages ListObjectsV2
until it is no longer truncated (10.g: no limit or cross-check runs over an unknown subset), and
refuses, before parsing, a page over `max_listing_bytes` or one carrying a DOCTYPE or ENTITY. A
row that does not parse is skipped and counted, as a torn index line is on disk.

**Failing.** A transport error, a timeout or a 5xx is `InputStoreUnavailable` (retryable). A
401 or 403 is an `InputStoreError` naming the credential variables, never their values. No
message, log record or URL carries a credential.

Declared by `interfaces/seaweedfs_input_store_interface.py::SeaweedFsInputStoreInterface`.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Final
from uuid import UUID
from xml.etree import ElementTree  # nosec B405 - pages are size-bounded and DOCTYPE-free

import httpx

from vibey.application.interfaces.system import Clock
from vibey.domain.errors import InputStoreError, InputStoreUnavailable
from vibey.domain.run_input import (
    RUN_INPUT_RULE,
    InputKind,
    InputListing,
    InputStoreLocation,
    RunInput,
    StoreProbe,
)
from vibey.infrastructure.blob.interfaces.s3_request_signer_interface import (
    S3RequestSignerInterface,
)

MAX_LISTING_BYTES: Final = 1_048_576
"""The largest ListObjectsV2 page read (1 MiB): a page of 1000 keys is about 300 KiB, so a larger
one is not an S3 listing, and it is refused before it is parsed."""
MAX_ROW_BYTES: Final = 4096
"""The largest index row object read, the same bound as the local store's index line."""
_EPOCH: Final = datetime(1970, 1, 1, tzinfo=UTC)
_CODE: Final = re.compile(rb"<Code>([^<]{1,128})</Code>")
_HOSTILE: Final = (b"<!doctype", b"<!entity")


class SeaweedFsInputStore:
    """Declared by `interfaces/seaweedfs_input_store_interface.py::SeaweedFsInputStoreInterface`."""

    def __init__(
        self,
        location: InputStoreLocation,
        clock: Clock,
        *,
        signer: S3RequestSignerInterface,
        client: httpx.Client,
        unique: Callable[[], str] = lambda: uuid.uuid4().hex,
        max_listing_bytes: int = MAX_LISTING_BYTES,
    ) -> None:
        if location.kind != "seaweedfs" or location.endpoint is None or location.bucket is None:
            raise ValueError("a SeaweedFS input store needs a seaweedfs [inputs] location")
        self._location = location
        self._clock = clock
        self._signer = signer
        self._client = client
        self._unique = unique
        self._max_listing = max_listing_bytes
        self._endpoint = location.endpoint.rstrip("/")
        self._host = httpx.URL(self._endpoint).netloc.decode("ascii")
        self._bucket = location.bucket

    # -- the port -----------------------------------------------------------------------------

    def put(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        item = RunInput(digest=RUN_INPUT_RULE.digest_of(data), kind=kind, name=name, size=len(data))
        row = self._row_bytes(item)
        key = self._object_key(project_id, item.digest)
        if not self._intact(key, item.digest, item.size):
            self._put_object(key, data)
        self._put_object(self._row_key(project_id), row)
        return item

    def restore(self, project_id: UUID, data: bytes) -> str:
        digest = RUN_INPUT_RULE.digest_of(data)
        self._put_object(self._object_key(project_id, digest), data)
        return digest

    def get(self, project_id: UUID, digest: str, *, size: int) -> bytes:
        if not RUN_INPUT_RULE.is_digest(digest):
            raise InputStoreError(f"{digest!r} is not a digest")
        key = self._object_key(project_id, digest)
        status, headers, body = self._exchange("GET", key, max_bytes=size, expected=size)
        if status == 404 and self._code(body) != "NoSuchBucket":
            raise InputStoreError(f"{self.describe()}: no stored input is {digest}")
        self._raise_for(status, body)
        if headers.get("content-length") != str(size):
            raise InputStoreError(
                f"{self.describe()}: the stored object {digest} is "
                f"{headers.get('content-length', 'of no stated')} bytes, not the {size} its row "
                "says; add that input again to store it afresh"
            )
        if len(body) != size or RUN_INPUT_RULE.digest_of(body) != digest:
            raise InputStoreError(
                f"{self.describe()}: the stored object {digest} does not match its digest; add "
                "that input again to store it afresh"
            )
        return body

    def listed(self, project_id: UUID) -> InputListing:
        items: list[RunInput] = []
        skipped = 0
        for key in self._keys(f"{self._base(project_id)}/index/"):
            status, _, body = self._exchange("GET", key, max_bytes=MAX_ROW_BYTES)
            if status == 404 and self._code(body) != "NoSuchBucket":
                skipped += 1  # listed, then gone: a row no longer there is not given
                continue
            self._raise_for(status, body)
            item = RUN_INPUT_RULE.row_of(body) if len(body) <= MAX_ROW_BYTES else None
            if item is None:
                skipped += 1
            else:
                items.append(item)
        return InputListing(items=tuple(items), skipped=skipped)

    # -- doctor -------------------------------------------------------------------------------

    def describe(self) -> str:
        return self._location.describe()

    def probe(self) -> StoreProbe:
        query = {"list-type": "2", "max-keys": "1", "prefix": f"{self._location.prefix}/"}
        try:
            status, _, body = self._exchange("GET", "", query=query, max_bytes=self._max_listing)
        except InputStoreUnavailable as exc:
            return StoreProbe(False, str(exc).removeprefix(f"{self.describe()}: "))
        failure = self._failure(status, body)
        if failure is None:
            return StoreProbe(True, "reachable")
        return StoreProbe(False, failure[1])

    # -- requests -----------------------------------------------------------------------------

    def _exchange(
        self,
        method: str,
        key: str,
        *,
        query: Mapping[str, str] | None = None,
        body: bytes = b"",
        max_bytes: int,
        expected: int | None = None,
    ) -> tuple[int, Mapping[str, str], bytes]:
        """One signed request to the endpoint: its status, its headers, and at most
        `max_bytes + 1` bytes of its body (of an error answer, at most `MAX_ROW_BYTES + 1`, enough
        for its S3 error code). With `expected`, a 200 whose `Content-Length` is not
        `expected` is answered with no body read at all."""
        uri = f"/{self._bucket}" + (f"/{key}" if key else "")
        query = dict(query or {})
        headers = self._signer.headers(
            method=method, host=self._host, canonical_uri=uri, query=query, body=body
        )
        canonical = self._signer.canonical_query(query)
        url = f"{self._endpoint}{uri}" + (f"?{canonical}" if canonical else "")
        try:
            with self._client.stream(method, url, headers=headers, content=body) as response:
                if (
                    expected is not None
                    and response.status_code == 200
                    and response.headers.get("content-length") != str(expected)
                ):
                    return response.status_code, dict(response.headers), b""
                # An error answer is read only as far as its S3 error code needs.
                limit = max_bytes if response.is_success else MAX_ROW_BYTES
                read = bytearray()
                if method != "HEAD":
                    for chunk in response.iter_bytes():
                        read += chunk
                        if len(read) > limit:
                            break
                return response.status_code, dict(response.headers), bytes(read[: limit + 1])
        except httpx.TransportError as exc:
            raise InputStoreUnavailable(
                f"{self.describe()}: not reachable ({type(exc).__name__})"
            ) from None

    def _raise_for(self, status: int, body: bytes) -> None:
        """Nothing for a 2xx; else the error `_failure` names, prefixed with the store."""
        failure = self._failure(status, body)
        if failure is not None:
            error, detail = failure
            raise error(f"{self.describe()}: {detail}")

    def _failure(self, status: int, body: bytes) -> tuple[type[InputStoreError], str] | None:
        """None for a 2xx; else the error class a status and its S3 error code call for, and
        the words that say why. A 5xx is retryable; the rest are not."""
        if 200 <= status < 300:
            return None
        if status >= 500:
            return InputStoreUnavailable, f"answered HTTP {status}"
        if status in (401, 403):
            names = f"{self._location.access_key_env}, {self._location.secret_key_env}"
            return InputStoreError, f"refused the credentials in {names}"
        if self._code(body) == "NoSuchBucket":
            return InputStoreError, (
                f"bucket {self._bucket} does not exist; vibey never creates one, so create it "
                "(scoped to these credentials) or name another in [inputs]"
            )
        if 300 <= status < 400:
            return InputStoreError, (
                f"answered with a redirect (HTTP {status}); vibey follows none, so name the "
                "store's own endpoint in [inputs]"
            )
        return InputStoreError, f"answered HTTP {status}"

    def _put_object(self, key: str, data: bytes) -> None:
        status, _, body = self._exchange("PUT", key, body=data, max_bytes=MAX_ROW_BYTES)
        self._raise_for(status, body)

    def _intact(self, key: str, digest: str, size: int) -> bool:
        """Whether the object at `key` is already there with exactly the bytes `digest` names."""
        status, headers, body = self._exchange("HEAD", key, max_bytes=0)
        if status == 404:
            return False
        self._raise_for(status, body)
        if headers.get("content-length") != str(size):
            return False
        status, _, body = self._exchange("GET", key, max_bytes=size, expected=size)
        if status == 404:
            return False
        self._raise_for(status, body)
        return len(body) == size and RUN_INPUT_RULE.digest_of(body) == digest

    def _keys(self, prefix: str) -> list[str]:
        """Every key under `prefix`, in the store's (lexical) order, over every page."""
        keys: list[str] = []
        token: str | None = None
        while True:
            query = {"list-type": "2", "prefix": prefix}
            if token is not None:
                query["continuation-token"] = token
            status, _, body = self._exchange("GET", "", query=query, max_bytes=self._max_listing)
            self._raise_for(status, body)
            page, token = self._page(body)
            keys.extend(page)
            if token is None:
                return keys

    def _page(self, body: bytes) -> tuple[list[str], str | None]:
        """One ListObjectsV2 page: its keys and, when it is truncated, the next token."""
        if len(body) > self._max_listing:
            raise InputStoreError(
                f"{self.describe()}: a listing page is over {self._max_listing} bytes; refused "
                "unread"
            )
        lowered = body.lower()
        if any(marker in lowered for marker in _HOSTILE):
            raise InputStoreError(
                f"{self.describe()}: a listing page carries a DOCTYPE or ENTITY; refused unread"
            )
        try:
            # nosec B314: the page is bounded and refused above when it carries a DOCTYPE or an
            # ENTITY, so no entity can expand; ElementTree resolves no external resource.
            root = ElementTree.fromstring(body)  # nosec B314
        except ElementTree.ParseError as exc:
            raise InputStoreError(f"{self.describe()}: a listing page is not XML") from exc
        keys = [
            (element.text or "") for element in root.iter() if self._local(element.tag) == "Key"
        ]
        truncated = any(
            self._local(element.tag) == "IsTruncated" and (element.text or "").strip() == "true"
            for element in root
        )
        if not truncated:
            return keys, None
        token = next(
            (
                (element.text or "")
                for element in root
                if self._local(element.tag) == "NextContinuationToken"
            ),
            "",
        )
        if not token:
            raise InputStoreError(
                f"{self.describe()}: a truncated listing page names no continuation token"
            )
        return keys, token

    # -- keys ---------------------------------------------------------------------------------

    def _base(self, project_id: UUID) -> str:
        return f"{self._location.prefix}/{project_id}"

    def _object_key(self, project_id: UUID, digest: str) -> str:
        return f"{self._base(project_id)}/objects/{digest[:2]}/{digest}"

    def _row_key(self, project_id: UUID) -> str:
        at = (self._clock.now().astimezone(UTC) - _EPOCH) // timedelta(microseconds=1) * 1000
        return f"{self._base(project_id)}/index/{at:020d}-{self._unique()}.json"

    def _row_bytes(self, item: RunInput) -> bytes:
        row = {
            "digest": item.digest,
            "kind": item.kind,
            "name": item.name,
            "size": item.size,
            "at": self._clock.now().isoformat(),
        }
        data = json.dumps(row, ensure_ascii=True, separators=(",", ":")).encode()
        if len(data) > MAX_ROW_BYTES:
            raise InputStoreError(
                f"the index row for this input is {len(data)} bytes; at most {MAX_ROW_BYTES} "
                "are stored"
            )
        return data

    @staticmethod
    def _code(body: bytes) -> str:
        match = _CODE.search(body)
        return match.group(1).decode("utf-8", "replace") if match else ""

    @staticmethod
    def _local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]
