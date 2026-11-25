# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey install --model`'s puller, against a fake Ollama: no network, no sleeps.

It waits a bounded time for Ollama to answer, pulls nothing when the model is there, streams
the pull's progress as readable lines, and refuses -- with the next step -- when there is no
Ollama, when it does not answer, and when the pull fails.
"""

from __future__ import annotations

import io
import json
import urllib.request
from typing import Any

import pytest

from vibey.infrastructure.interfaces.ollama_pull_interface import OllamaModelPullerInterface
from vibey.infrastructure.ollama_pull import OllamaModelPuller

TAG = "hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE"


class _Response(io.BytesIO):
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()


class _Ollama:
    """Answers /api/version, /api/tags, /api/show and /api/pull as declared."""

    def __init__(
        self,
        *,
        models: tuple[str, ...] = (),
        pull: tuple[dict[str, Any], ...] = ({"status": "success"},),
        down_for: int = 0,
        broken_pull: bool = False,
    ) -> None:
        self.models = models
        self.pull = pull
        self.down_for = down_for
        self.broken_pull = broken_pull
        self.requests: list[tuple[str, dict[str, Any] | None]] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
        path = request.full_url.split("11434", 1)[1]
        body = json.loads(request.data) if request.data else None  # type: ignore[arg-type]
        self.requests.append((path, body))
        if self.down_for > 0:
            self.down_for -= 1
            raise OSError("connection refused")
        if path == "/api/version":
            return _Response(b'{"version": "0.12.0"}')
        if path == "/api/tags":
            return _Response(json.dumps({"models": [{"name": m} for m in self.models]}).encode())
        if path == "/api/show":
            return _Response(b"{}")
        if self.broken_pull:
            raise OSError("reset by peer")
        lines = b"\n".join(json.dumps(event).encode() for event in self.pull) + b"\n\n"
        return _Response(lines)


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def _puller(ollama: _Ollama, *, ollama_on_path: bool = True, wait: float = 3.0) -> Any:
    clock = _Clock()
    puller = OllamaModelPuller(
        "http://127.0.0.1:11434",
        opener=ollama,
        which=lambda name: "/usr/local/bin/ollama" if ollama_on_path else None,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        wait_seconds=wait,
    )
    return puller, clock


def _said() -> tuple[list[str], Any]:
    lines: list[str] = []
    return lines, lines.append


def test_the_puller_satisfies_its_interface() -> None:
    assert isinstance(_puller(_Ollama())[0], OllamaModelPullerInterface)


def test_a_model_that_is_there_is_not_pulled_again() -> None:
    ollama = _Ollama(models=(TAG,))
    lines, say = _said()
    result = _puller(ollama)[0].install(TAG, say, "about 12.1 GB")
    assert result.ok and not result.changed
    assert "already" in result.detail and TAG in result.detail
    assert not any(path == "/api/pull" for path, _ in ollama.requests)
    assert lines == []


def test_a_library_tag_without_a_version_matches_its_latest() -> None:
    result = _puller(_Ollama(models=("llama3:latest",)))[0].install("llama3", _said()[1], None)
    assert result.ok and not result.changed


def test_a_missing_model_is_pulled_with_its_size_said_first_and_its_progress_readable() -> None:
    events = (
        {"status": "pulling manifest"},
        {"status": "pulling abc", "digest": "abc", "total": 100, "completed": 0},
        {"status": "pulling abc", "digest": "abc", "total": 100, "completed": 5},
        {"status": "pulling abc", "digest": "abc", "total": 100, "completed": 100},
        {"status": "verifying sha256 digest"},
        {"status": "success"},
    )
    ollama = _Ollama(pull=events)
    lines, say = _said()
    result = _puller(ollama)[0].install(TAG, say, "about 12.1 GB")
    assert result.ok and result.changed and TAG in result.detail
    assert lines[0].startswith(f"Pulling {TAG} into the Ollama at http://127.0.0.1:11434")
    assert "about 12.1 GB" in lines[0]
    assert lines[1:] == [
        "  pulling manifest",
        "  pulling abc: 0% of 0.0 GB",
        "  pulling abc: 100% of 0.0 GB",
        "  verifying sha256 digest",
        "  success",
    ]
    assert ("/api/pull", {"model": TAG, "stream": True}) in ollama.requests


def test_a_model_of_unknown_size_says_so_before_the_pull() -> None:
    lines, say = _said()
    _puller(_Ollama())[0].install("qwen3:14b", say, None)
    assert "size" in lines[0] and "not known" in lines[0]


def test_an_ollama_that_starts_late_is_waited_for_within_the_bound() -> None:
    ollama = _Ollama(down_for=2)
    puller, clock = _puller(ollama, wait=5.0)
    assert puller.install(TAG, _said()[1], None).ok
    assert clock.slept == [1.0, 1.0]


def test_no_ollama_on_this_machine_is_refused_with_how_to_install_it() -> None:
    puller, clock = _puller(_Ollama(down_for=99), ollama_on_path=False, wait=2.0)
    result = puller.install(TAG, _said()[1], None)
    assert not result.ok and not result.changed
    assert "not installed" in result.detail
    assert "https://ollama.com/download" in result.detail
    assert "vibey install --model" in result.detail
    assert clock.now >= 2.0


def test_an_installed_ollama_that_does_not_answer_is_refused_with_how_to_start_it() -> None:
    puller, _ = _puller(_Ollama(down_for=99), wait=0.0)
    result = puller.install(TAG, _said()[1], None)
    assert not result.ok
    assert "ollama serve" in result.detail and "VIBEY_OLLAMA_URL" in result.detail


def test_an_ollama_that_answers_its_version_but_not_its_models_is_refused() -> None:
    class _NoTags(_Ollama):
        def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
            if request.full_url.endswith("/api/tags"):
                raise OSError("boom")
            return super().__call__(request, timeout)

    result = _puller(_NoTags())[0].install(TAG, _said()[1], None)
    assert not result.ok and "boom" in result.detail


@pytest.mark.parametrize(
    ("ollama", "said"),
    [
        (
            _Ollama(pull=({"status": "pulling manifest"}, {"error": "file does not exist"})),
            "does not exist",
        ),
        (_Ollama(pull=({"status": "pulling manifest"},)), "before Ollama said success"),
        (_Ollama(broken_pull=True), "reset by peer"),
    ],
)
def test_a_pull_that_fails_says_why_and_how_to_try_again(ollama: _Ollama, said: str) -> None:
    result = _puller(ollama)[0].install(TAG, _said()[1], None)
    assert not result.ok and result.changed is False
    assert said in result.detail and "vibey install --model" in result.detail


def test_a_garbled_stream_line_fails_the_pull() -> None:
    class _Garbled(_Ollama):
        def __call__(self, request: urllib.request.Request, timeout: float) -> _Response:
            if request.full_url.endswith("/api/pull"):
                return _Response(b"not json\n")
            return super().__call__(request, timeout)

    result = _puller(_Garbled())[0].install(TAG, _said()[1], None)
    assert not result.ok


@pytest.mark.parametrize("url", ["file:///etc/passwd", "127.0.0.1:11434", "http://"])
def test_an_endpoint_that_is_not_an_http_url_with_a_host_is_refused(url: str) -> None:
    with pytest.raises(ValueError, match="VIBEY_OLLAMA_URL"):
        OllamaModelPuller(url)


def test_the_defaults_are_the_real_clock_and_opener() -> None:
    puller = OllamaModelPuller("https://ollama.example:443/")
    assert isinstance(puller, OllamaModelPullerInterface)
