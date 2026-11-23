# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SeaweedFS input store over the S3 API (SP-LOOPS Phase 3c, Task 4; ADR-0105).

The fake is an in-memory S3 behind `httpx.MockTransport` (`tests/fakes/s3.py`), which checks
every request's SigV4 signature: no SeaweedFS, no network, a fixed clock, no thread, no sleep.
Module-level test functions: the class-and-interface rule is about production code (ADR-0016).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest

from tests.fakes.s3 import ACCESS, BUCKET, ENDPOINT, REGION, SECRET, FakeS3
from vibey.application.interfaces.input_store_interface import InputStoreInterface
from vibey.domain.errors import InputStoreError, InputStoreUnavailable
from vibey.domain.run_input import InputStoreLocation, StoreProbe
from vibey.infrastructure.blob.s3_request_signer import S3RequestSigner
from vibey.infrastructure.inputs.interfaces.seaweedfs_input_store_interface import (
    SeaweedFsInputStoreInterface,
)
from vibey.infrastructure.inputs.seaweedfs_input_store import SeaweedFsInputStore

AT = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)
PID = UUID("6f1c2a0e-0000-4000-8000-000000000001")
LOCATION = InputStoreLocation(kind="seaweedfs", endpoint=ENDPOINT, bucket=BUCKET)
ABC = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class _Clock:
    def now(self) -> datetime:
        return AT


def _store(
    fake: FakeS3, *, location: InputStoreLocation = LOCATION, **kwargs: object
) -> SeaweedFsInputStore:
    counter = iter(range(1_000_000))
    return SeaweedFsInputStore(
        location,
        _Clock(),
        signer=S3RequestSigner(ACCESS, SECRET, REGION, clock=lambda: AT),
        client=fake.client(),
        unique=lambda: f"{next(counter):032x}",
        **kwargs,  # type: ignore[arg-type]
    )


def _object_key(digest: str, project: UUID = PID) -> str:
    return f"vibey/inputs/{project}/objects/{digest[:2]}/{digest}"


def _rows(fake: FakeS3) -> list[str]:
    return sorted(key for key in fake.objects if "/index/" in key)


def test_the_store_meets_both_interfaces() -> None:
    store = _store(FakeS3())
    assert isinstance(store, InputStoreInterface)
    assert isinstance(store, SeaweedFsInputStoreInterface)


def test_a_location_that_is_not_seaweedfs_is_refused() -> None:
    with pytest.raises(ValueError, match="needs a seaweedfs"):
        _store(FakeS3(), location=InputStoreLocation())


def test_put_twice_writes_one_object_and_two_rows() -> None:
    fake = FakeS3()
    store = _store(fake)
    first = store.put(PID, "file", "spec.md", b"abc")
    second = store.put(PID, "file", "spec.md", b"abc")
    assert first == second
    puts = [r for r in fake.requests if r.method == "PUT"]
    object_puts = [r for r in puts if "/objects/" in r.url.path]
    assert len(object_puts) == 1  # the second add found the object intact
    assert len(_rows(fake)) == 2
    assert fake.objects[_object_key(ABC)] == b"abc"


def test_an_object_changed_in_the_bucket_is_written_again_by_put() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")
    fake.objects[_object_key(ABC)] = b"abd"  # same size, other bytes
    store.put(PID, "file", "a.txt", b"abc")
    assert fake.objects[_object_key(ABC)] == b"abc"
    fake.objects[_object_key(ABC)] = b"abcd"  # another size: HEAD alone says it is not intact
    store.put(PID, "file", "a.txt", b"abc")
    assert fake.objects[_object_key(ABC)] == b"abc"


def test_an_object_gone_between_head_and_get_is_written_again() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")

    def gone_on_get(request: httpx.Request) -> httpx.Response | None:
        if request.method == "GET" and "/objects/" in request.url.path:
            return httpx.Response(404, content=b"<Error><Code>NoSuchKey</Code></Error>")
        return None

    fake.answer = gone_on_get
    store.put(PID, "file", "a.txt", b"abc")
    assert sum(1 for r in fake.requests if r.method == "PUT" and "/objects/" in r.url.path) == 2


def test_get_returns_the_exact_bytes_with_nul_and_invalid_utf8() -> None:
    fake = FakeS3()
    store = _store(fake)
    data = b"\x00\xff\xfe raw \x80"
    item = store.put(PID, "file", "blob.bin", data)
    assert store.get(PID, item.digest, size=item.size) == data


def test_get_refuses_a_content_length_other_than_the_row_size_unread() -> None:
    fake = FakeS3()
    store = _store(fake)
    item = store.put(PID, "file", "a.txt", b"abc")
    streamed: list[bool] = []

    class _Watched(httpx.ByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            streamed.append(True)
            yield b"abcdef"

    fake.answer = lambda request: (
        httpx.Response(200, headers={"content-length": "6"}, stream=_Watched(b"abcdef"))
        if request.method == "GET" and "/objects/" in request.url.path
        else None
    )
    with pytest.raises(InputStoreError, match="is 6 bytes, not the 3 its row says"):
        store.get(PID, item.digest, size=item.size)
    assert streamed == []  # refused from its length, its body never read


def test_get_refuses_an_answer_with_no_length() -> None:
    fake = FakeS3()
    store = _store(fake)
    item = store.put(PID, "file", "a.txt", b"abc")

    def chunked(request: httpx.Request) -> httpx.Response | None:
        if request.method == "GET" and "/objects/" in request.url.path:
            response = httpx.Response(200, content=b"abc")
            del response.headers["content-length"]
            return response
        return None

    fake.answer = chunked
    with pytest.raises(InputStoreError, match="of no stated bytes"):
        store.get(PID, item.digest, size=item.size)


def test_get_refuses_bytes_that_do_not_match_their_digest() -> None:
    fake = FakeS3()
    store = _store(fake)
    item = store.put(PID, "file", "a.txt", b"abc")
    fake.objects[_object_key(ABC)] = b"xyz"  # a writer of the bucket swapped the bytes
    with pytest.raises(InputStoreError, match="does not match its digest"):
        store.get(PID, item.digest, size=item.size)


def test_get_refuses_a_body_longer_than_its_stated_length() -> None:
    fake = FakeS3()
    store = _store(fake)
    item = store.put(PID, "file", "a.txt", b"abc")

    class _Long(httpx.ByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            yield b"ab"
            yield b"cd"
            yield b"ef"

    fake.answer = lambda request: (
        httpx.Response(200, headers={"content-length": "3"}, stream=_Long(b""))
        if request.method == "GET" and "/objects/" in request.url.path
        else None
    )
    with pytest.raises(InputStoreError, match="does not match its digest"):
        store.get(PID, item.digest, size=item.size)


def test_get_of_a_missing_object_or_a_non_digest_is_an_error() -> None:
    store = _store(FakeS3())
    with pytest.raises(InputStoreError, match="no stored input is"):
        store.get(PID, ABC, size=3)
    with pytest.raises(InputStoreError, match="is not a digest"):
        store.get(PID, "../etc/passwd", size=3)


def test_listed_is_the_add_order() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "paste", "paste", b"one")
    store.put(PID, "file", "b.txt", b"two")
    listing = store.listed(PID)
    assert [item.name for item in listing.items] == ["paste", "b.txt"]
    assert listing.skipped == 0


def test_listed_follows_every_continuation_token() -> None:
    fake = FakeS3(page_size=2)
    store = _store(fake)
    for n in range(5):
        store.put(PID, "file", f"f{n}.txt", f"data {n}".encode())
    listing = store.listed(PID)
    assert [item.name for item in listing.items] == [f"f{n}.txt" for n in range(5)]
    lists = [r for r in fake.requests if r.url.params.get("list-type") == "2"]
    assert [r.url.params.get("continuation-token") for r in lists] == [None, "tok-2", "tok-4"]


def test_a_project_with_nothing_stored_is_an_empty_listing() -> None:
    listing = _store(FakeS3()).listed(PID)
    assert listing.items == () and listing.skipped == 0


@pytest.mark.parametrize(
    "row",
    [
        b"not json",
        b"[1, 2]",
        json.dumps({"digest": "nope", "kind": "file", "name": "a", "size": 1}).encode(),
        b"x" * 5000,
    ],
)
def test_a_row_that_is_not_json_is_skipped_and_counted(row: bytes) -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")
    fake.objects[f"vibey/inputs/{PID}/index/00000000000000000000-{'f' * 32}.json"] = row
    listing = store.listed(PID)
    assert listing.skipped == 1
    assert [item.name for item in listing.items] == ["a.txt"]


def test_a_row_listed_then_gone_is_skipped() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")
    fake.answer = lambda request: (
        httpx.Response(404, content=b"<Error><Code>NoSuchKey</Code></Error>")
        if request.method == "GET" and "/index/" in request.url.path
        else None
    )
    assert store.listed(PID).skipped == 1


def test_a_listing_with_a_doctype_or_over_one_mib_is_refused() -> None:
    fake = FakeS3()
    store = _store(fake)
    hostile = (
        b'<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">]>'
        b"<ListBucketResult><IsTruncated>false</IsTruncated></ListBucketResult>"
    )
    fake.answer = lambda request: (
        httpx.Response(200, content=hostile) if "list-type" in request.url.params else None
    )
    with pytest.raises(InputStoreError, match="carries a DOCTYPE or ENTITY"):
        store.listed(PID)
    fake.answer = lambda request: (
        httpx.Response(200, content=b"<a>" + b" " * 1_048_577 + b"</a>")
        if "list-type" in request.url.params
        else None
    )
    with pytest.raises(InputStoreError, match="over 1048576 bytes"):
        store.listed(PID)


def test_a_listing_that_is_not_xml_or_has_no_token_is_refused() -> None:
    fake = FakeS3()
    store = _store(fake)
    fake.answer = lambda request: (
        httpx.Response(200, content=b"<unclosed>") if "list-type" in request.url.params else None
    )
    with pytest.raises(InputStoreError, match="is not XML"):
        store.listed(PID)
    fake.answer = lambda request: (
        httpx.Response(
            200, content=b"<ListBucketResult><IsTruncated>true</IsTruncated></ListBucketResult>"
        )
        if "list-type" in request.url.params
        else None
    )
    with pytest.raises(InputStoreError, match="names no continuation token"):
        store.listed(PID)


def test_restore_writes_the_object_and_no_row() -> None:
    fake = FakeS3()
    store = _store(fake)
    assert store.restore(PID, b"abc") == ABC
    assert fake.objects == {_object_key(ABC): b"abc"}


def test_object_and_row_keys_follow_the_layout() -> None:
    fake = FakeS3()
    _store(fake).put(PID, "file", "a.txt", b"abc")
    assert _object_key(ABC) == f"vibey/inputs/{PID}/objects/ba/{ABC}"
    assert _object_key(ABC) in fake.objects
    [row_key] = _rows(fake)
    at_ns = int(AT.timestamp()) * 1_000_000_000
    assert row_key == f"vibey/inputs/{PID}/index/{at_ns:020d}-{0:032x}.json"
    row = json.loads(fake.objects[row_key])
    assert row == {"digest": ABC, "kind": "file", "name": "a.txt", "size": 3, "at": AT.isoformat()}


def test_a_row_too_large_to_store_is_refused_before_anything_is_written() -> None:
    fake = FakeS3()
    with pytest.raises(InputStoreError, match="index row for this input"):
        _store(fake).put(PID, "file", "\x01" * 700, b"abc")  # escaped, each is 6 bytes
    assert fake.requests == []


def test_every_request_is_signed_and_goes_only_to_the_endpoint() -> None:
    fake = FakeS3()
    store = _store(fake)
    item = store.put(PID, "file", "a.txt", b"abc")
    store.get(PID, item.digest, size=item.size)
    store.listed(PID)
    assert fake.requests
    for request in fake.requests:  # the fake has checked each signature already
        assert request.headers["authorization"].startswith(
            "AWS4-HMAC-SHA256 Credential=FAKEACCESS/"
        )
        assert request.url.scheme == "https"
        assert request.url.netloc == b"files.example.test:8333"
        assert request.url.path.startswith(f"/{BUCKET}")


def test_the_secret_appears_in_no_request_url_header_or_log_record(
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake = FakeS3()
    store = _store(fake)
    with caplog.at_level(logging.DEBUG):
        item = store.put(PID, "file", "a.txt", b"abc")
        store.get(PID, item.digest, size=item.size)
        store.listed(PID)
        store.probe()
    for request in fake.requests:
        assert SECRET not in str(request.url)
        assert all(SECRET not in value for value in request.headers.values())
    assert all(SECRET not in record.getMessage() for record in caplog.records)
    assert SECRET not in repr(store.__dict__)


def test_a_403_is_a_store_error_naming_the_variables_not_the_values() -> None:
    fake = FakeS3()
    store = _store(fake)
    fake.answer = lambda request: httpx.Response(
        403, content=b"<Error><Code>SignatureDoesNotMatch</Code></Error>"
    )
    with pytest.raises(InputStoreError) as caught:
        store.listed(PID)
    assert not isinstance(caught.value, InputStoreUnavailable)
    message = str(caught.value)
    assert "VIBEY_INPUTS_ACCESS_KEY, VIBEY_INPUTS_SECRET_KEY" in message
    assert SECRET not in message and ACCESS not in message


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("refused"),
        httpx.ReadTimeout("slow"),
        httpx.Response(503),
        httpx.Response(500),
    ],
)
def test_a_transport_error_or_503_is_unavailable(failure: object) -> None:
    fake = FakeS3()
    store = _store(fake)

    def answer(request: httpx.Request) -> httpx.Response | None:
        if isinstance(failure, Exception):
            raise failure
        assert isinstance(failure, httpx.Response)
        return failure

    fake.answer = answer
    with pytest.raises(InputStoreUnavailable) as caught:
        store.put(PID, "file", "a.txt", b"abc")
    assert "seaweedfs store https://files.example.test:8333/vibey-inputs/vibey/inputs" in str(
        caught.value
    )
    assert not _rows(fake)


def test_a_missing_bucket_is_never_created() -> None:
    fake = FakeS3(buckets=())
    store = _store(fake)
    with pytest.raises(InputStoreError, match="bucket vibey-inputs does not exist"):
        store.put(PID, "file", "a.txt", b"abc")
    with pytest.raises(InputStoreError, match="vibey never creates one"):
        store.listed(PID)
    with pytest.raises(InputStoreError, match="does not exist"):
        store.get(PID, ABC, size=3)
    assert not any(r.method == "PUT" and r.url.path == f"/{BUCKET}" for r in fake.requests)
    assert fake.buckets == set()


def test_a_listed_row_whose_bucket_vanished_is_an_error_not_a_skip() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")
    fake.answer = lambda request: (
        httpx.Response(404, content=b"<Error><Code>NoSuchBucket</Code></Error>")
        if "/index/" in request.url.path
        else None
    )
    with pytest.raises(InputStoreError, match="does not exist"):
        store.listed(PID)


@pytest.mark.parametrize(
    ("status", "message"),
    [(301, "answered with a redirect"), (400, "answered HTTP 400"), (409, "answered HTTP 409")],
)
def test_a_redirect_or_another_status_is_an_error_never_followed(status: int, message: str) -> None:
    fake = FakeS3()
    store = _store(fake)
    fake.answer = lambda request: httpx.Response(
        status, headers={"location": "https://elsewhere.test/"}
    )
    with pytest.raises(InputStoreError, match=message):
        store.restore(PID, b"abc")
    assert all(r.url.host == "files.example.test" for r in fake.requests)


def test_a_head_that_fails_stops_put_before_any_write() -> None:
    fake = FakeS3()
    store = _store(fake)
    fake.answer = lambda request: httpx.Response(403) if request.method == "HEAD" else None
    with pytest.raises(InputStoreError, match="refused the credentials"):
        store.put(PID, "file", "a.txt", b"abc")
    assert fake.objects == {}


def test_a_get_that_fails_while_checking_stops_put_before_any_write() -> None:
    fake = FakeS3()
    store = _store(fake)
    store.restore(PID, b"abc")
    fake.answer = lambda request: httpx.Response(403) if request.method == "GET" else None
    with pytest.raises(InputStoreError, match="refused the credentials"):
        store.put(PID, "file", "a.txt", b"abc")
    assert not _rows(fake)


def test_probe_answers_reachable() -> None:
    fake = FakeS3()
    assert _store(fake).probe() == StoreProbe(True, "reachable")
    [request] = fake.requests
    assert request.url.params["max-keys"] == "1"
    assert request.url.params["prefix"] == "vibey/inputs/"


@pytest.mark.parametrize(
    ("answer", "detail"),
    [
        (httpx.ConnectError("x"), "not reachable (ConnectError)"),
        (httpx.Response(503), "answered HTTP 503"),
        (httpx.Response(403), "refused the credentials in VIBEY_INPUTS_ACCESS_KEY, "),
        (
            httpx.Response(404, content=b"<Error><Code>NoSuchBucket</Code></Error>"),
            "bucket vibey-inputs does not exist",
        ),
    ],
)
def test_probe_says_why_it_failed_and_never_raises(answer: object, detail: str) -> None:
    fake = FakeS3()

    def respond(request: httpx.Request) -> httpx.Response:
        if isinstance(answer, Exception):
            raise answer
        assert isinstance(answer, httpx.Response)
        return answer

    fake.answer = respond
    probe = _store(fake).probe()
    assert probe.reachable is False
    assert probe.detail.startswith(detail)
    assert SECRET not in probe.detail


def test_describe_is_the_locations() -> None:
    assert _store(FakeS3()).describe() == LOCATION.describe()


# -- fix round 1: keys, bounds, hostile listings, error classes (review I1, N2-N6) -------------


def test_a_key_with_a_space_signs_as_it_is_sent() -> None:
    """The signed path is the percent-encoded path, so S3 (and the fake, which re-signs the
    decoded key as S3 does) agrees: no 403."""
    fake = FakeS3()
    store = _store(fake)
    key = "vibey/inputs/odd key/ünïcode~x.txt"
    status, _, _ = store._exchange("PUT", key, body=b"x", max_bytes=10)  # noqa: SLF001
    assert status == 200
    assert fake.objects[key] == b"x"
    assert b"odd%20key" in fake.requests[-1].url.raw_path


def test_a_store_signing_with_the_wrong_secret_gets_s3s_403() -> None:
    fake = FakeS3(secret="another-secret")
    with pytest.raises(InputStoreError, match="refused the credentials"):
        _store(fake).listed(PID)


@pytest.mark.parametrize(
    "planted",
    [
        "a b.json",
        "../../../other/x.json",
        "00000000000000000000-zz.json",
        "sub/00000000000000000000-" + "0" * 32 + ".json",
        "00000000000000000000-" + "0" * 32 + ".json?x",
    ],
)
def test_a_planted_key_is_skipped_and_never_fetched(planted: str) -> None:
    fake = FakeS3()
    store = _store(fake)
    store.put(PID, "file", "a.txt", b"abc")
    fake.objects[f"vibey/inputs/{PID}/index/{planted}"] = b"{}"
    before = len(fake.requests)
    listing = store.listed(PID)
    assert [item.name for item in listing.items] == ["a.txt"]
    assert listing.skipped == 1
    fetched = [r for r in fake.requests[before:] if "list-type" not in r.url.params]
    assert len(fetched) == 1  # the one real row; the planted key was never requested


def test_a_listing_past_max_listed_rows_is_refused_unread() -> None:
    fake = FakeS3()
    location = InputStoreLocation(
        kind="seaweedfs", endpoint=ENDPOINT, bucket=BUCKET, max_listed_rows=2
    )
    store = _store(fake, location=location)
    for n in range(3):
        store.put(PID, "paste", "paste", f"p{n}".encode())
    before = len(fake.requests)
    with pytest.raises(
        InputStoreError, match="lists 3 rows; \\[inputs\\] max_listed_rows reads at most 2"
    ):
        store.listed(PID)
    assert all("list-type" in r.url.params for r in fake.requests[before:])


def _page(token: str | None, keys: tuple[str, ...] = ()) -> httpx.Response:
    contents = "".join(f"<Contents><Key>{k}</Key></Contents>" for k in keys)
    truncated = "true" if token else "false"
    tail = f"<NextContinuationToken>{token}</NextContinuationToken>" if token else ""
    return httpx.Response(
        200,
        content=(
            f"<ListBucketResult><IsTruncated>{truncated}</IsTruncated>{contents}{tail}"
            "</ListBucketResult>"
        ).encode(),
    )


def test_a_repeated_continuation_token_is_refused_not_followed_forever() -> None:
    fake = FakeS3()
    fake.answer = lambda request: _page("same") if "list-type" in request.url.params else None
    with pytest.raises(InputStoreError, match="repeated a continuation token"):
        _store(fake).listed(PID)
    assert len(fake.requests) == 2


def test_a_listing_that_never_ends_is_refused_at_the_page_bound() -> None:
    fake = FakeS3()
    counter = iter(range(10_000))
    fake.answer = lambda request: (
        _page(f"t{next(counter)}") if "list-type" in request.url.params else None
    )
    location = InputStoreLocation(
        kind="seaweedfs", endpoint=ENDPOINT, bucket=BUCKET, max_listed_rows=3
    )
    with pytest.raises(InputStoreError, match="ran past 4 pages"):
        _store(fake, location=location).listed(PID)
    assert len(fake.requests) == 4


@pytest.mark.parametrize(
    "body",
    [
        b"\xef\xbb\xbf<ListBucketResult/>",
        "<?xml version='1.0' encoding='utf-16'?><!DOCTYPE x><a/>".encode("utf-16"),
        b"<ListBucketResult>\x00</ListBucketResult>",
    ],
)
def test_a_listing_that_is_not_plain_utf8_is_refused(body: bytes) -> None:
    fake = FakeS3()
    fake.answer = lambda request: (
        httpx.Response(200, content=body) if "list-type" in request.url.params else None
    )
    with pytest.raises(InputStoreError, match="not plain UTF-8"):
        _store(fake).listed(PID)


@pytest.mark.parametrize(
    "error",
    [httpx.DecodingError("bad gzip"), httpx.InvalidURL("bad"), ValueError("x"), OverflowError("x")],
)
def test_an_error_httpx_raises_outside_the_transport_is_a_store_error_not_a_crash(
    error: Exception,
) -> None:
    fake = FakeS3()

    def fail(request: httpx.Request) -> httpx.Response:
        raise error

    fake.answer = fail
    with pytest.raises(InputStoreError) as caught:
        _store(fake).restore(PID, b"abc")
    assert not isinstance(caught.value, InputStoreUnavailable)
    assert type(error).__name__ in str(caught.value)
