# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/guarded_opener.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

import urllib.request
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GuardedOpenerInterface(Protocol):
    """Opens one search backend's requests: same-origin redirects only, and no proxy between
    vibey and a loopback SearXNG."""

    direct: bool
    """Whether requests skip the environment's proxy (the backend is on loopback)."""

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        """The response, as `urllib.request.urlopen` returns it."""
        ...
