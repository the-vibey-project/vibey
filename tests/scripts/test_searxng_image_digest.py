# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/searxng_image_digest.py`: how the pinned SearXNG image is refreshed by hand
(ADR-0102). The registry is a fake opener: no test calls the network (SP-ACP Task 9d, P-9d-2).
"""

from __future__ import annotations

import io
import json
import urllib.request
from email.message import Message
from typing import Any

import pytest

from scripts.interfaces.searxng_image_digest_interface import RegistryDigestInterface
from scripts.searxng_image_digest import (
    ACCEPT,
    REGISTRY,
    REPOSITORY,
    TIMEOUT_SECONDS,
    TOKEN_URL,
    RegistryDigest,
    main,
)

DIGEST = "sha256:" + "ab" * 32


class _Answer:
    """What `urlopen` hands back, as a context manager: a body and headers."""

    def __init__(self, body: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self._body = io.BytesIO(body)
        self.headers = Message()
        for name, value in (headers or {}).items():
            self.headers[name] = value

    def __enter__(self) -> _Answer:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self._body.read(limit)


class _Registry:
    """Docker Hub as the script sees it: an anonymous token, then a HEAD of the manifest."""

    def __init__(self, token: Any = "t0k3n", digest: str = DIGEST) -> None:
        self.token = token
        self.digest = digest
        self.calls: list[tuple[Any, float]] = []

    def __call__(self, target: Any, *, timeout: float) -> _Answer:
        self.calls.append((target, timeout))
        if isinstance(target, str):
            return _Answer(json.dumps({"token": self.token}).encode())
        return _Answer(headers={"Docker-Content-Digest": self.digest})


def test_the_reader_honours_its_interface() -> None:
    reader: RegistryDigestInterface = RegistryDigest(_Registry())  # checked by mypy
    assert callable(reader.digest)


def test_the_digest_is_read_with_an_anonymous_token_and_a_head_of_the_manifest() -> None:
    registry = _Registry()

    assert RegistryDigest(registry).digest(REPOSITORY, "2026.11.1-abc") == DIGEST

    (token_url, first), (request, second) = registry.calls
    assert token_url == (
        f"{TOKEN_URL}?service=registry.docker.io&scope=repository%3A{REPOSITORY.replace('/', '%2F')}"
        "%3Apull"
    )
    assert isinstance(request, urllib.request.Request)
    assert request.get_method() == "HEAD"
    assert request.full_url == f"{REGISTRY}/v2/{REPOSITORY}/manifests/2026.11.1-abc"
    assert request.get_header("Authorization") == "Bearer t0k3n"
    assert request.get_header("Accept") == ACCEPT
    assert first == second == TIMEOUT_SECONDS


def test_a_tag_is_quoted_into_the_path() -> None:
    registry = _Registry()
    RegistryDigest(registry).digest(REPOSITORY, "a/b?c")
    assert registry.calls[1][0].full_url.endswith("/manifests/a%2Fb%3Fc")


@pytest.mark.parametrize("token", [None, "", 3])
def test_no_token_is_refused(token: Any) -> None:
    with pytest.raises(RuntimeError, match="no anonymous pull token"):
        RegistryDigest(_Registry(token=token)).digest(REPOSITORY, "latest")


@pytest.mark.parametrize("digest", ["", "sha256:short", "md5:" + "a" * 64, DIGEST.upper()])
def test_an_answer_that_is_not_a_sha256_digest_is_refused(digest: str) -> None:
    with pytest.raises(RuntimeError, match="no sha256 digest"):
        RegistryDigest(_Registry(digest=digest)).digest(REPOSITORY, "latest")


class _Fixed:
    def __init__(self, answer: str | Exception) -> None:
        self.answer = answer
        self.asked: list[tuple[str, str]] = []

    def digest(self, repository: str, tag: str) -> str:
        self.asked.append((repository, tag))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_main_prints_the_line_to_paste_and_where_it_was_read(
    capsys: pytest.CaptureFixture[str],
) -> None:
    registry = _Fixed(DIGEST)

    assert main(["--tag", "edge"], registry=registry) == 0

    out = capsys.readouterr().out.splitlines()
    assert registry.asked == [(REPOSITORY, "edge")]
    assert out[0] == f'SEARXNG_IMAGE: Final = "docker.io/{REPOSITORY}@{DIGEST}"'
    assert out[1].startswith("# read ") and out[1].endswith(
        f"from {REGISTRY} ({REPOSITORY}:edge, anonymous HEAD)"
    )


def test_main_reads_latest_by_default(capsys: pytest.CaptureFixture[str]) -> None:
    registry = _Fixed(DIGEST)
    assert main([], registry=registry) == 0
    assert registry.asked == [(REPOSITORY, "latest")]


@pytest.mark.parametrize(
    "failure", [OSError("unreachable"), ValueError("bad json"), RuntimeError("no digest")]
)
def test_main_says_what_failed_and_exits_1(
    failure: Exception, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main([], registry=_Fixed(failure)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"could not read {REPOSITORY}:latest: {failure}\n"
