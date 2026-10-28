# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The OpenBao and Nextcloud adapters bound every call with a timeout, and refuse one that bounds
nothing (gap K3; sub-doctrine 12.c: the bound is the declared `[surfaces]` key)."""

import json
from types import TracebackType
from typing import Any

import pytest

from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.files.nextcloud import NextcloudFilesAdapter
from vibey.infrastructure.secrets.openbao import OpenBaoSecretsAdapter


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _RecordingOpener:
    """The `opener=` seam: answers every request and remembers the timeout it was given."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.timeouts: list[float | None] = []

    def __call__(self, request: object, timeout: float | None = None) -> _Response:
        self.timeouts.append(timeout)
        return _Response(self._body)


_SECRET = json.dumps({"data": {"data": {"value": "v"}}}).encode()


async def _exercise_openbao(opener: _RecordingOpener, **kwargs: float) -> None:
    adapter = OpenBaoSecretsAdapter(url="http://bao", token="t", opener=opener, **kwargs)
    await adapter.set_secret("k", "v")
    assert await adapter.get_secret("k") == "v"


async def _exercise_nextcloud(opener: _RecordingOpener, **kwargs: float) -> None:
    adapter = NextcloudFilesAdapter(
        url="http://nc", user="u", password="p", opener=opener, **kwargs
    )
    await adapter.upload_file("a/b.txt", b"x")
    assert await adapter.download_file("a/b.txt") == _SECRET


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [({}, DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS), ({"timeout": 2.5}, 2.5)],
)
async def test_openbao_get_and_set_carry_the_timeout(
    kwargs: dict[str, float], expected: float
) -> None:
    opener = _RecordingOpener(_SECRET)
    await _exercise_openbao(opener, **kwargs)
    assert opener.timeouts == [expected, expected]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [({}, DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS), ({"timeout": 2.5}, 2.5)],
)
async def test_nextcloud_upload_and_download_carry_the_timeout(
    kwargs: dict[str, float], expected: float
) -> None:
    opener = _RecordingOpener(_SECRET)
    await _exercise_nextcloud(opener, **kwargs)
    assert opener.timeouts == [expected, expected]


@pytest.mark.parametrize("bad", [0, -1, -0.5])
def test_both_refuse_a_non_positive_timeout(bad: float) -> None:
    builders: list[Any] = [
        lambda: OpenBaoSecretsAdapter(url="http://bao", token="t", timeout=bad),
        lambda: NextcloudFilesAdapter(url="http://nc", user="u", password="p", timeout=bad),
    ]
    for build in builders:
        with pytest.raises(ValueError, match="timeout must be positive"):
            build()
