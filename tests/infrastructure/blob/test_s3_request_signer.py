# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One S3 SigV4 signer for the family (SP-LOOPS Phase 3c, Task 3; ADR-0105 OR-3).

The signer was extracted from `GarageBlobAdapter`, which signed every S3 request itself. The
characterization test pins the exact `Authorization` header Garage produced before the extraction,
for a PUT with a body and a GET, at a fixed clock and with fake keys; it passed on the old code
and must pass unchanged on the new. Module-level test functions (ADR-0016 is about production
code). No network: the opener is a recorder.
"""

from __future__ import annotations

import urllib.request
from datetime import UTC, datetime
from typing import Any

import pytest

from vibey.infrastructure.blob import garage as garage_module
from vibey.infrastructure.blob.garage import GarageBlobAdapter
from vibey.infrastructure.blob.interfaces.s3_request_signer_interface import (
    S3RequestSignerInterface,
)
from vibey.infrastructure.blob.s3_request_signer import S3RequestSigner

FIXED = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
ACCESS = "FAKEACCESS"
SECRET = "fake-secret-sentinel"

PUT_AUTHORIZATION = (
    "AWS4-HMAC-SHA256 Credential=FAKEACCESS/20260102/us-east-1/s3/aws4_request, "
    "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, "
    "Signature=46d2b571e88c4510b02de880ce4143db9ed5a1e484b3175cb8e5fc19e6d56bd2"
)
GET_AUTHORIZATION = (
    "AWS4-HMAC-SHA256 Credential=FAKEACCESS/20260102/us-east-1/s3/aws4_request, "
    "SignedHeaders=host;x-amz-content-sha256;x-amz-date, "
    "Signature=1bfde15e1cbc921765ef70769eb3ef1c14d6ee5db63ae936089f5ec5abb79e88"
)


class _FixedDatetime(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
        return FIXED


class _Response:
    status = 200

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return b"body"


class _Recorder:
    def __init__(self) -> None:
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        self.requests.append(request)
        return _Response()


def _garage(recorder: _Recorder) -> GarageBlobAdapter:
    return GarageBlobAdapter(
        url="https://garage.example.test:3900",
        access_key=ACCESS,
        secret_key=SECRET,
        opener=recorder,
    )


def _authorizations(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(garage_module, "datetime", _FixedDatetime)
    recorder = _Recorder()
    adapter = _garage(recorder)
    adapter._put_sync("bucket", "dir/key.bin", b"\x00payload\xff", "text/plain")  # noqa: SLF001
    adapter._get_sync("bucket", "dir/key.bin")  # noqa: SLF001
    create, put, get = recorder.requests
    return {
        "create": str(create.get_header("Authorization")),
        "put": str(put.get_header("Authorization")),
        "get": str(get.get_header("Authorization")),
    }


def test_garage_signs_exactly_as_before_extraction(monkeypatch: pytest.MonkeyPatch) -> None:
    signed = _authorizations(monkeypatch)
    assert signed["put"] == PUT_AUTHORIZATION
    assert signed["get"] == GET_AUTHORIZATION


def _signer(secret: str = SECRET, region: str = "us-east-1") -> S3RequestSigner:
    return S3RequestSigner(ACCESS, secret, region, clock=lambda: FIXED)


def test_signer_headers_equal_garages_for_the_same_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    garage = _authorizations(monkeypatch)
    signer = _signer()
    put = signer.headers(
        method="PUT",
        host="garage.example.test:3900",
        canonical_uri="/bucket/dir/key.bin",
        query={},
        body=b"\x00payload\xff",
        signed={"Content-Type": "text/plain"},
    )
    get = signer.headers(
        method="GET",
        host="garage.example.test:3900",
        canonical_uri="/bucket/dir/key.bin",
        query={},
        body=b"",
    )
    assert put["Authorization"] == garage["put"]
    assert get["Authorization"] == garage["get"]
    assert put["content-type"] == "text/plain"
    assert set(get) == {"host", "x-amz-content-sha256", "x-amz-date", "Authorization"}
    assert get["x-amz-date"] == "20260102T030405Z"
    assert get["x-amz-content-sha256"] == (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


AWS_ACCESS = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
AWS_DATE = datetime(2013, 5, 24, tzinfo=UTC)


def test_the_signer_reproduces_awss_published_get_object_example() -> None:
    """AWS's own worked example for S3 SigV4 ("Example: GET Object"), so the signer is right on
    its own terms and not only equal to what Garage did before."""
    signer = S3RequestSigner(AWS_ACCESS, AWS_SECRET, "us-east-1", clock=lambda: AWS_DATE)
    headers = signer.headers(
        method="GET",
        host="examplebucket.s3.amazonaws.com",
        canonical_uri="/test.txt",
        query={},
        body=b"",
        signed={"Range": "bytes=0-9"},
    )
    assert headers["Authorization"] == (
        "AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
        "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
        "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41"
    )


def test_the_signer_reproduces_awss_published_list_objects_example() -> None:
    """AWS's worked example "GET Bucket (List Objects)": a query string is canonicalized."""
    signer = S3RequestSigner(AWS_ACCESS, AWS_SECRET, "us-east-1", clock=lambda: AWS_DATE)
    headers = signer.headers(
        method="GET",
        host="examplebucket.s3.amazonaws.com",
        canonical_uri="/",
        query={"prefix": "J", "max-keys": "2"},
        body=b"",
    )
    assert headers["Authorization"].endswith(
        "Signature=34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7"
    )


def test_the_canonical_query_is_sorted_and_strictly_encoded() -> None:
    assert _signer().canonical_query({"b": "x y/z", "a": "~-_.", "list-type": "2"}) == (
        "a=~-_.&b=x%20y%2Fz&list-type=2"
    )
    assert _signer().canonical_query({}) == ""


def test_the_signer_repr_holds_no_secret() -> None:
    signer = _signer(secret="s3cr3t-sentinel")
    assert "s3cr3t-sentinel" not in repr(signer)
    assert "s3cr3t-sentinel" not in str(signer)
    assert not hasattr(signer, "__dict__")  # slots: no attribute dump that could carry it
    headers = signer.headers(method="GET", host="h", canonical_uri="/", query={}, body=b"")
    assert all("s3cr3t-sentinel" not in value for value in headers.values())
    assert signer.access_key == ACCESS


def test_the_signer_meets_its_interface() -> None:
    assert isinstance(_signer(), S3RequestSignerInterface)


def test_a_clock_in_another_zone_is_signed_in_utc() -> None:
    from datetime import timedelta, timezone

    later = datetime(2026, 1, 2, 5, 4, 5, tzinfo=timezone(timedelta(hours=2)))
    signer = S3RequestSigner(ACCESS, SECRET, "us-east-1", clock=lambda: later)
    headers = signer.headers(method="GET", host="h", canonical_uri="/", query={}, body=b"")
    assert headers["x-amz-date"] == "20260102T030405Z"
