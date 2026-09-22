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
