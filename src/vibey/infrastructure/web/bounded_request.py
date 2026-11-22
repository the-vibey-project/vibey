# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One search request, its headers and body read in full, under a total deadline.

A socket timeout bounds each read, not the request: a listener that sends one byte just inside
it every time -- in the status line, the headers or the body -- holds a reader for as long as it
likes. So the whole request (open, headers, body up to `limit` bytes) runs on a daemon thread
and the caller waits at most the deadline. When the deadline passes, the caller gets
`DeadlineExceeded` and moves on; the thread is left to end when its socket does (it is a daemon,
so it never holds the process open), and its result is dropped.

Declared by `interfaces/bounded_request_interface.py` (ADR-0016).
"""

from __future__ import annotations

import threading
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class DeadlineExceeded(TimeoutError):
    """The request did not finish within its total deadline."""


@dataclass(frozen=True, slots=True)
class Answered:
    """What came back: at most `limit` bytes of body, and the URL the response came from."""

    body: bytes
    url: str


class BoundedRequest:
    """Declared by `interfaces/bounded_request_interface.py::BoundedRequestInterface`."""

    def __init__(self, opener: Callable[..., Any]) -> None:
        self._opener = opener

    def fetch(self, request: urllib.request.Request, *, deadline: float, limit: int) -> Answered:
        """The answer, or the opener's own exception, or `DeadlineExceeded` after `deadline`
        seconds in all."""
        outcome: list[Answered | BaseException] = []

        def run() -> None:
            try:
                with self._opener(request, timeout=deadline) as response:
                    landed = getattr(response, "url", None) or request.full_url
                    outcome.append(Answered(response.read(limit), landed))
            except BaseException as exc:  # noqa: BLE001 - handed back to the caller as it was
                outcome.append(exc)

        worker = threading.Thread(target=run, name="vibey-search-request", daemon=True)
        worker.start()
        worker.join(deadline)
        if not outcome:
            raise DeadlineExceeded(f"no complete answer within {deadline:g}s")
        result = outcome[0]
        if isinstance(result, BaseException):
            raise result
        return result
