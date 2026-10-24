# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The models an Ollama has, and what it says each can do (ADR-0093, #1662).

Capabilities come from Ollama's own `/api/show`, never from a table in vibey: Ollama decides
tool-calling from more than a model's template (a built-in renderer counts), so a list kept
here would be wrong for exactly the newer models. An Ollama too old to report capabilities,
or a model it will not describe, gives `None` -- unknown, which is not the same as "none".
"""

import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class OllamaUnavailable(RuntimeError):
    """No Ollama answered at the address."""


@dataclass(frozen=True, slots=True)
class InstalledModel:
    tag: str
    size_bytes: int
    capabilities: frozenset[str] | None


class OllamaModels:
    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        timeout_seconds: float = 5.0,
    ) -> None:
        # The opener is a seam, not a setting: tests hand in a double (ADR-0016).
        self._base = base_url.rstrip("/")
        self._opener = opener
        self._timeout = timeout_seconds

    def installed(self) -> tuple[InstalledModel, ...]:
        try:
            listing = self._json(urllib.request.Request(f"{self._base}/api/tags"))
        except (OSError, ValueError) as exc:
            raise OllamaUnavailable(f"no Ollama answered at {self._base}: {exc}") from exc
        entries = listing.get("models", []) if isinstance(listing, dict) else []
        models = [entry for entry in entries if isinstance(entry, dict) and "name" in entry]
        return tuple(
            InstalledModel(
                str(entry["name"]),
                int(entry.get("size", 0)),
                self.capabilities(str(entry["name"])),
            )
            for entry in models
        )

    def capabilities(self, tag: str) -> frozenset[str] | None:
        """What Ollama reports for `tag`, or None when it does not say."""
        request = urllib.request.Request(
            f"{self._base}/api/show",
            data=json.dumps({"model": tag}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            shown = self._json(request)
        except (OSError, ValueError):
            return None
        reported = shown.get("capabilities") if isinstance(shown, dict) else None
        if not isinstance(reported, list):
            return None
        return frozenset(str(item) for item in reported)

    def _json(self, request: urllib.request.Request) -> Any:
        with self._opener(request, timeout=self._timeout) as response:
            return json.loads(response.read())
