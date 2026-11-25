# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pulling the local model into Ollama, for `vibey install --model`.

Through the Ollama at `VIBEY_OLLAMA_URL` (the one endpoint setting), never the `ollama` command:
the same HTTP API every other part of vibey talks to, so it works for an Ollama on another host
as well as for this one. It waits a bounded time for Ollama to answer (a service that was just
started may not listen yet), asks `OllamaModels` -- `vibey models`' own client -- whether the
model is already there, and pulls nothing when it is. Otherwise it says the model and its
download size first, then streams `POST /api/pull` through `PullProgress`, so the progress
reads the same in a terminal and under `curl | sh`.

Every refusal names the next step: install Ollama, start it, or run the command again (a pull
that stopped resumes where it was, since Ollama keeps the layers it finished).

Declared by `interfaces/ollama_pull_interface.py` (ADR-0016).
"""

from __future__ import annotations

import json
import shutil
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Final

from vibey.domain.interfaces.model_pull_interface import PullProgressInterface
from vibey.domain.model_pull import PullProgress
from vibey.infrastructure.ollama_models import DEFAULT_OLLAMA_URL, OllamaModels, OllamaUnavailable

OLLAMA_URL_ENV: Final = "VIBEY_OLLAMA_URL"
OLLAMA_DOWNLOAD_PAGE: Final = "https://ollama.com/download"
RETRY_COMMAND: Final = "vibey install --model"
DEFAULT_WAIT_SECONDS: Final = 30.0
#: How long one read of the pull's stream may stay silent; a large layer streams throughout.
DEFAULT_READ_TIMEOUT_SECONDS: Final = 300.0
_PROBE_TIMEOUT_SECONDS: Final = 5.0
_POLL_SECONDS: Final = 1.0
_HTTP_SCHEMES: Final = ("http", "https")
_LATEST: Final = ":latest"


@dataclass(frozen=True, slots=True)
class ModelInstallResult:
    """What `install` did: `ok`, whether it pulled anything, and what to say."""

    ok: bool
    changed: bool
    detail: str


class OllamaModelPuller:
    """Declared by `OllamaModelPullerInterface`. The opener, `which`, the clock and the
    progress reporter are seams, not settings: tests hand in doubles (ADR-0016)."""

    def __init__(
        self,
        base_url: str = DEFAULT_OLLAMA_URL,
        *,
        opener: Callable[..., Any] = urllib.request.urlopen,
        which: Callable[[str], str | None] = shutil.which,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        wait_seconds: float = DEFAULT_WAIT_SECONDS,
        read_timeout_seconds: float = DEFAULT_READ_TIMEOUT_SECONDS,
        progress: Callable[[], PullProgressInterface] = PullProgress,
    ) -> None:
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in _HTTP_SCHEMES or not parts.hostname:
            raise ValueError(
                f"{OLLAMA_URL_ENV} must be an http(s) URL with a host, not {base_url!r}"
            )
        self._base = base_url.rstrip("/")
        self._opener = opener
        self._which = which
        self._sleep = sleep
        self._monotonic = monotonic
        self._wait = wait_seconds
        self._read_timeout = read_timeout_seconds
        self._progress = progress

    def install(self, tag: str, say: Callable[[str], None], size: str | None) -> ModelInstallResult:
        if not self._answering():
            return ModelInstallResult(False, False, self._unreachable())
        try:
            installed = OllamaModels(self._base, opener=self._opener).installed()
        except OllamaUnavailable as exc:
            return ModelInstallResult(False, False, f"{exc}; run `{RETRY_COMMAND}` again")
        names = {model.tag for model in installed}
        if tag in names or (_LATEST not in tag and f"{tag}{_LATEST}" in names):
            return ModelInstallResult(
                True, False, f"{tag} is already in the Ollama at {self._base}; nothing to pull"
            )
        weight = (
            f"a download of {size}" if size else "its size is not known until Ollama reports it"
        )
        say(f"Pulling {tag} into the Ollama at {self._base}: {weight}.")
        problem = self._pull(tag, say)
        if problem is not None:
            return ModelInstallResult(
                False,
                False,
                f"the pull of {tag} failed: {problem}. Run `{RETRY_COMMAND}` again; Ollama "
                "keeps the parts it finished",
            )
        return ModelInstallResult(True, True, f"{tag} is in the Ollama at {self._base}")

    def _answering(self) -> bool:
        started = self._monotonic()
        while True:
            request = urllib.request.Request(f"{self._base}/api/version")  # nosec B310 - http(s) checked
            try:
                with self._opener(request, timeout=_PROBE_TIMEOUT_SECONDS) as response:
                    json.loads(response.read())
                return True
            except (OSError, ValueError):
                if self._monotonic() - started >= self._wait:
                    return False
                self._sleep(_POLL_SECONDS)

    def _unreachable(self) -> str:
        if self._which("ollama") is None:
            return (
                f"Ollama is not installed here (no `ollama` on PATH, and nothing answered at "
                f"{self._base}). Install it -- macOS: `brew install ollama && brew services "
                f"start ollama`, or the app from {OLLAMA_DOWNLOAD_PAGE}; Linux: the installer "
                f"on {OLLAMA_DOWNLOAD_PAGE} -- then run `{RETRY_COMMAND}` again"
            )
        return (
            f"Ollama is installed but nothing answered at {self._base} within "
            f"{self._wait:g}s. Start it (`ollama serve`, `brew services start ollama`, or open "
            f"the Ollama app), then run `{RETRY_COMMAND}` again; {OLLAMA_URL_ENV} names "
            "another server"
        )

    def _pull(self, tag: str, say: Callable[[str], None]) -> str | None:
        """None when Ollama said success; otherwise why not."""
        request = urllib.request.Request(  # nosec B310 - http(s) checked in __init__
            f"{self._base}/api/pull",
            data=json.dumps({"model": tag, "stream": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        progress = self._progress()
        succeeded = False
        try:
            with self._opener(request, timeout=self._read_timeout) as response:
                for raw in response:
                    if not raw.strip():
                        continue
                    event = json.loads(raw)
                    if "error" in event:
                        return str(event["error"])
                    line = progress.line(event)
                    if line is not None:
                        say(f"  {line}")
                    succeeded = succeeded or event.get("status") == "success"
        except (OSError, ValueError) as exc:
            return str(exc)
        return None if succeeded else "the stream ended before Ollama said success"
