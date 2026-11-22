# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey searxng serve`, what the SearXNG unit runs (ADR-0102).

Implemented by `infrastructure/searxng/searxng_serve.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SearxngServeInterface(Protocol):
    def run(self) -> int:
        """Check the person's record, the settings and the image, then replace this process
        with the container runtime's one command line; never downloads. Returns only on a
        refusal (said on standard error), with its exit code."""
        ...
