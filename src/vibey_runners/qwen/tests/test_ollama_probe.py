# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import urllib.error

import pytest

from qwenloop.application.interfaces import OllamaProbeInterface
from qwenloop.infrastructure.ollama_probe import DEFAULT_OLLAMA_VERSION_URL, OllamaProbe


class Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "Response":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


def test_the_probe_asks_ollamas_version_endpoint_with_a_short_timeout() -> None:
    asked: list[tuple[str, float]] = []

    def opener(url: str, *, timeout: float) -> Response:
        asked.append((url, timeout))
        return Response(200)

    probe = OllamaProbe(opener=opener)
    assert isinstance(probe, OllamaProbeInterface)
    assert probe.available() is True
    assert asked == [("http://127.0.0.1:11434/api/version", 2.0)]
    assert DEFAULT_OLLAMA_VERSION_URL == "http://127.0.0.1:11434/api/version"


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError("connection refused"),
        urllib.error.HTTPError("http://x", 500, "error", {}, None),  # type: ignore[arg-type]
        TimeoutError("timed out"),
        ValueError("unknown url type"),
    ],
)
def test_any_failure_means_ollama_is_not_available(failure: Exception) -> None:
    def opener(url: str, *, timeout: float) -> Response:
        raise failure

    assert OllamaProbe(opener=opener).available() is False


def test_an_answer_other_than_ok_is_not_ollama() -> None:
    assert OllamaProbe(opener=lambda url, *, timeout: Response(204)).available() is False


class _Shown:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Shown":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _show_opener(body: bytes, asked: list[tuple[str, bytes]] | None = None):  # type: ignore[no-untyped-def]
    def opener(request, *, timeout):  # type: ignore[no-untyped-def]
        if asked is not None:
            asked.append((request.full_url, request.data))
        return _Shown(body)

    return opener


def test_the_model_probe_asks_the_ollama_root_not_its_openai_prefix() -> None:
    from qwenloop.application.interfaces import OllamaModelProbeInterface
    from qwenloop.infrastructure.ollama_probe import OllamaModelProbe

    asked: list[tuple[str, bytes]] = []
    probe = OllamaModelProbe(opener=_show_opener(b'{"capabilities":["completion","tools"]}', asked))
    assert isinstance(probe, OllamaModelProbeInterface)
    assert probe.capabilities("http://127.0.0.1:11434/v1/", "m:1") == {"completion", "tools"}
    assert asked == [("http://127.0.0.1:11434/api/show", b'{"model": "m:1"}')]


@pytest.mark.parametrize(
    "body", [b'{"license":"x"}', b'{"capabilities":"tools"}', b"[1]", b"not json"]
)
def test_a_model_probe_answer_that_is_not_a_capability_list_is_unknown(body: bytes) -> None:
    from qwenloop.infrastructure.ollama_probe import OllamaModelProbe

    assert OllamaModelProbe(opener=_show_opener(body)).capabilities("http://x/v1", "m") is None


def test_a_server_that_is_not_an_ollama_is_unknown() -> None:
    from qwenloop.infrastructure.ollama_probe import OllamaModelProbe

    def refuses(request, *, timeout):  # type: ignore[no-untyped-def]
        raise urllib.error.HTTPError("http://x", 404, "no", {}, None)  # type: ignore[arg-type]

    assert OllamaModelProbe(opener=refuses).capabilities("http://x/v1", "m") is None
