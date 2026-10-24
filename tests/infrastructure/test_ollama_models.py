# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import io
import json
from typing import Any

import pytest

from vibey.infrastructure.interfaces.ollama_models_interface import OllamaModelsInterface
from vibey.infrastructure.ollama_models import (
    InstalledModel,
    OllamaModels,
    OllamaUnavailable,
)


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *exc: object) -> None:
        return None


class _Ollama:
    """A fake Ollama: answers by path, or raises what a down server raises."""

    def __init__(self, answers: dict[str, Any], *, down: bool = False) -> None:
        self.answers, self.down, self.requests = answers, down, []

    def __call__(self, request: Any, timeout: float) -> _Response:
        path = request.full_url.rpartition("11434")[2]
        self.requests.append((path, request.data))
        if self.down:
            raise ConnectionRefusedError("refused")
        answer = self.answers[path if path != "/api/show" else request.data.decode()]
        if isinstance(answer, Exception):
            raise answer
        return _Response(answer if isinstance(answer, bytes) else json.dumps(answer).encode())


def _show(tag: str) -> str:
    return json.dumps({"model": tag})


def test_the_client_satisfies_its_interface() -> None:
    assert isinstance(OllamaModels(), OllamaModelsInterface)


def test_installed_models_carry_what_ollama_reports_for_each() -> None:
    opener = _Ollama(
        {
            "/api/tags": {"models": [{"name": "a:1", "size": 5}, {"name": "b:2"}, "junk", {}]},
            _show("a:1"): {"capabilities": ["completion", "tools"]},
            _show("b:2"): {"license": "no capabilities field"},
        }
    )
    models = OllamaModels("http://127.0.0.1:11434/", opener=opener).installed()
    assert models == (
        InstalledModel("a:1", 5, frozenset({"completion", "tools"})),
        InstalledModel("b:2", 0, None),
    )


def test_no_ollama_is_an_error_that_says_where() -> None:
    client = OllamaModels(opener=_Ollama({}, down=True))
    with pytest.raises(OllamaUnavailable, match="127.0.0.1:11434"):
        client.installed()


def test_a_listing_that_is_not_an_object_is_no_models() -> None:
    assert OllamaModels(opener=_Ollama({"/api/tags": ["x"]})).installed() == ()


def test_a_model_ollama_will_not_describe_is_unknown_not_empty() -> None:
    boom = OSError("404")
    client = OllamaModels(opener=_Ollama({_show("x:1"): boom, _show("y:1"): b"not json"}))
    assert client.capabilities("x:1") is None
    assert client.capabilities("y:1") is None


def test_capabilities_that_are_not_a_list_are_unknown() -> None:
    client = OllamaModels(
        opener=_Ollama({_show("z:1"): {"capabilities": "tools"}, _show("w:1"): ["x"]})
    )
    assert client.capabilities("z:1") is None
    assert client.capabilities("w:1") is None
