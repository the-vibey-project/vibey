# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/bounded_request.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

import urllib.request
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.web.bounded_request import Answered


@runtime_checkable
class BoundedRequestInterface(Protocol):
    """Runs one request, headers and body, under a total deadline."""

    def fetch(self, request: urllib.request.Request, *, deadline: float, limit: int) -> Answered:
        """At most `limit` bytes of body and the URL it came from; raises the opener's error, or
        `DeadlineExceeded` when `deadline` seconds pass first."""
        ...
