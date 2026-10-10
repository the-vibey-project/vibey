# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What `vibey doctor` says about the model Ollama is holding.

Ollama keeps a model loaded at the context it was loaded with, and reloads it when a request
asks for a different one. A model warmed up at a very large window and left resident makes
the first real request pay for a reload, with a key-value cache sized for that window: on a
laptop that was the difference between a DESIGN call answering and the same call timing out
at 900 seconds. Nothing flagged it, because the server was healthy and the model was loaded.
This asks `/api/ps` what is resident and says so when it is larger than the context vibey's
requests are held to (`VIBEY_OLLAMA_CONTEXT`).

A WARN is never a failure: the check reads a server that may belong to someone else, and an
absent server is a skipped line, not a red one.
"""

import asyncio
import json
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any, Final

from vibey.infrastructure.engines.ollama_chat import (
    DEFAULT_OLLAMA_CONTEXT,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    OLLAMA_CONTEXT_ENV,
    OLLAMA_MODEL_ENV,
    OLLAMA_URL_ENV,
)

PROBE_TIMEOUT_SECONDS: Final[float] = 3.0
_HTTP_SCHEMES: Final = ("http", "https")


class OllamaResidency:
    """Reads `/api/ps` and describes the configured model's residency in one line."""

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout: float = PROBE_TIMEOUT_SECONDS,
    ) -> None:
        self._opener = opener
        self._timeout = timeout

    async def line(self, environ: Mapping[str, str]) -> str:
        url = (environ.get(OLLAMA_URL_ENV) or DEFAULT_OLLAMA_URL).strip().rstrip("/")
        model = (environ.get(OLLAMA_MODEL_ENV) or DEFAULT_OLLAMA_MODEL).strip()
        raw_ceiling = (environ.get(OLLAMA_CONTEXT_ENV) or str(DEFAULT_OLLAMA_CONTEXT)).strip()
        try:
            ceiling = int(raw_ceiling)
        except ValueError:
            return f"ollama   WARN: {OLLAMA_CONTEXT_ENV} is not a whole number of tokens"
        loaded = await asyncio.to_thread(self._loaded, url)
        if loaded is None:
            return (
                f"ollama   SKIP: no server answered at {_where(url)}"
                f" (the local engines need one; {OLLAMA_URL_ENV})"
            )
        resident = next((m for m in loaded if _is(m, model)), None)
        if resident is None:
            return f"ollama   OK: {model} is not loaded; the first request loads it"
        context = resident.get("context_length")
        if not isinstance(context, int) or isinstance(context, bool):
            return f"ollama   OK: {model} is loaded (this Ollama does not report its context)"
        if context > ceiling:
            return (
                f"ollama   WARN: {model} is loaded at a context of {context}, above the {ceiling}"
                f" its requests are held to ({OLLAMA_CONTEXT_ENV}). Ollama reloads a model whose"
                " context differs from a request's, so the first request pays for it and may"
                f" time out. Unload it: ollama stop {model}"
            )
        return (
            f"ollama   OK: {model} is loaded at a context of {context},"
            f" within the {ceiling} requests are held to"
        )

    def _loaded(self, url: str) -> list[dict[str, Any]] | None:
        """The models Ollama reports loaded, or None when no server answered."""
        try:
            if urllib.parse.urlsplit(url).scheme not in _HTTP_SCHEMES:
                return None
            request = urllib.request.Request(f"{url}/api/ps")  # nosec B310 - scheme checked
            with self._opener(request, timeout=self._timeout) as response:
                body = json.loads(response.read())
        except (OSError, ValueError):
            return None
        models = body.get("models") if isinstance(body, dict) else None
        if not isinstance(models, list):
            return None
        return [m for m in models if isinstance(m, dict)]


def _is(entry: Mapping[str, Any], model: str) -> bool:
    """Whether `/api/ps` names `model`. Ollama lists an untagged name with `:latest`."""
    names = {entry.get("model"), entry.get("name")}
    return model in names or (":" not in model and f"{model}:latest" in names)


def _where(url: str) -> str:
    """Host and port only: a URL can carry `user:token@`, and this reaches a terminal."""
    try:
        parts = urllib.parse.urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError:
        return "the configured address"
    host = host or "the configured address"
    return f"{host}:{port}" if port else host
