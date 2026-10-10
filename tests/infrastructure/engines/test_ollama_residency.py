# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey doctor` says about the model Ollama is holding."""

import json
import urllib.request
from typing import Any

import pytest

from vibey.infrastructure.engines.ollama_residency import OllamaResidency


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def read(self) -> bytes:
        return self._body


def _serving(body: object) -> Any:
    seen: list[tuple[str, float]] = []

    def opener(request: urllib.request.Request, timeout: float) -> _Response:
        seen.append((request.full_url, timeout))
        return _Response(body if isinstance(body, bytes) else json.dumps(body).encode())

    opener.seen = seen  # type: ignore[attr-defined]
    return opener


async def _line(body: object, environ: dict[str, str] | None = None) -> str:
    return await OllamaResidency(opener=_serving(body)).line(environ or {})


async def test_a_model_loaded_far_above_the_requests_context_is_warned_about() -> None:
    line = await _line({"models": [{"model": "gpt-oss:20b", "context_length": 131072}]})
    assert line.startswith("ollama   WARN: gpt-oss:20b is loaded at a context of 131072")
    assert "above the 8192" in line and "VIBEY_OLLAMA_CONTEXT" in line
    assert "ollama stop gpt-oss:20b" in line


async def test_a_model_loaded_within_the_ceiling_is_fine() -> None:
    line = await _line({"models": [{"name": "gpt-oss:20b", "context_length": 8192}]})
    assert (
        line
        == "ollama   OK: gpt-oss:20b is loaded at a context of 8192, within the 8192 requests are held to"
    )


async def test_the_ceiling_and_model_come_from_the_environment() -> None:
    env = {"VIBEY_OLLAMA_CONTEXT": "32768", "VIBEY_OLLAMA_MODEL": "qwen3:14b"}
    line = await _line({"models": [{"model": "qwen3:14b", "context_length": 20000}]}, env)
    assert line.startswith("ollama   OK: qwen3:14b is loaded at a context of 20000")
    assert "within the 32768" in line


async def test_an_untagged_name_matches_ollamas_latest_tag() -> None:
    env = {"VIBEY_OLLAMA_MODEL": "mymodel"}
    line = await _line({"models": [{"model": "mymodel:latest", "context_length": 99999}]}, env)
    assert "WARN: mymodel is loaded" in line


async def test_a_model_that_is_not_loaded_is_said_to_load_on_first_use() -> None:
    line = await _line({"models": [{"model": "other:1b", "context_length": 8192}, "odd"]})
    assert line == "ollama   OK: gpt-oss:20b is not loaded; the first request loads it"


@pytest.mark.parametrize("context", [None, "8192", True])
async def test_an_ollama_that_does_not_report_context_is_not_second_guessed(
    context: object,
) -> None:
    line = await _line({"models": [{"model": "gpt-oss:20b", "context_length": context}]})
    assert line == "ollama   OK: gpt-oss:20b is loaded (this Ollama does not report its context)"


@pytest.mark.parametrize("body", [b"not json", [1], {"models": "no"}, {"nothing": 1}])
async def test_an_answer_that_is_not_ollamas_counts_as_no_server(body: object) -> None:
    assert (await _line(body)).startswith("ollama   SKIP: no server answered at 127.0.0.1:11434")


async def test_no_server_is_a_skip_that_names_host_and_port_but_never_credentials() -> None:
    def refused(*args: object, **kwargs: object) -> None:
        raise ConnectionRefusedError

    env = {"VIBEY_OLLAMA_URL": "http://user:sekret@gpu-box:9999/"}
    line = await OllamaResidency(opener=refused).line(env)
    assert "no server answered at gpu-box:9999" in line
    assert "sekret" not in line and "user" not in line


@pytest.mark.parametrize(
    ("url", "named"),
    [
        ("file:///etc/passwd", "the configured address"),
        ("http://[::1", "the configured address"),
    ],
)
async def test_a_url_that_is_not_http_is_never_opened(url: str, named: str) -> None:
    opener = _serving({"models": []})
    line = await OllamaResidency(opener=opener).line({"VIBEY_OLLAMA_URL": url})
    assert line.startswith("ollama   SKIP: no server answered")
    assert opener.seen == []


async def test_a_host_without_a_port_is_named_alone() -> None:
    def refused(*args: object, **kwargs: object) -> None:
        raise OSError

    line = await OllamaResidency(opener=refused).line(
        {"VIBEY_OLLAMA_URL": "https://models.example"}
    )
    assert "no server answered at models.example " in line


async def test_the_probe_is_short_and_asks_api_ps() -> None:
    opener = _serving({"models": []})
    await OllamaResidency(opener=opener, timeout=1.5).line({"VIBEY_OLLAMA_URL": "http://h:1/"})
    assert opener.seen == [("http://h:1/api/ps", 1.5)]


async def test_a_context_setting_that_is_not_a_number_is_said_not_crashed_on() -> None:
    line = await _line({"models": []}, {"VIBEY_OLLAMA_CONTEXT": "big"})
    assert line == "ollama   WARN: VIBEY_OLLAMA_CONTEXT is not a whole number of tokens"


async def test_a_port_that_is_out_of_range_is_named_as_the_configured_address() -> None:
    def refused(*args: object, **kwargs: object) -> None:
        raise OSError

    line = await OllamaResidency(opener=refused).line({"VIBEY_OLLAMA_URL": "http://host:99999999"})
    assert "no server answered at the configured address " in line
