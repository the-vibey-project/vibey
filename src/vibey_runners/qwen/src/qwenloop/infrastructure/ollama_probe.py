# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a local Ollama is running at its default address.

With nothing configured, a running Ollama is qwenloop's default backend (#388): it
serves this era's default model (sub-doctrine 8.d) and needs nothing downloaded twice.
"""

import json
import urllib.request
from collections.abc import Callable
from typing import Any

from qwenloop.domain.config import DEFAULT_ENDPOINT_BASE_URL

#: Ollama's own version endpoint, beside the OpenAI-compatible API qwenloop attaches to.
DEFAULT_OLLAMA_VERSION_URL = DEFAULT_ENDPOINT_BASE_URL.removesuffix("/v1") + "/api/version"


class OllamaProbe:
    def __init__(
        self,
        url: str = DEFAULT_OLLAMA_VERSION_URL,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout_seconds: float = 2.0,
    ) -> None:
        # The opener is a seam, not a setting: tests hand in a double instead of
        # patching urllib (ADR-0016).
        self._url = url
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def available(self) -> bool:
        try:
            with self._opener(self._url, timeout=self._timeout_seconds) as response:
                return bool(response.status == 200)
        except (OSError, ValueError):
            # URLError and HTTPError are OSErrors; a refused, slow or failing Ollama
            # is simply not the default backend this time.
            return False


class OllamaModelProbe:
    """What an Ollama says a model can do, from its own `/api/show`.

    Asked of the endpoint a run is about to attach to. Anything that is not an Ollama (vLLM,
    LM Studio, a gateway) has no `/api/show` and answers None, so the guard that reads this
    never stops a run it cannot speak for.
    """

    def __init__(
        self,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout_seconds: float = 5.0,
    ) -> None:
        self._opener = opener
        self._timeout_seconds = timeout_seconds

    def capabilities(self, base_url: str, model: str) -> frozenset[str] | None:
        root = base_url.rstrip("/").removesuffix("/v1")
        request = urllib.request.Request(  # noqa: S310 - the endpoint the run attaches to anyway
            f"{root}/api/show",
            data=json.dumps({"model": model}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with self._opener(request, timeout=self._timeout_seconds) as response:
                shown = json.loads(response.read())
        except (OSError, ValueError):
            return None
        reported = shown.get("capabilities") if isinstance(shown, dict) else None
        if not isinstance(reported, list):
            return None
        return frozenset(str(item) for item in reported)
