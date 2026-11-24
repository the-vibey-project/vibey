# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of the token estimate a loop's capability budgets are measured in (SP-LOOPS Phase 5,
R8)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenEstimateInterface(Protocol):
    def tokens(self, text: str) -> int:
        """What `text` is estimated to cost: its length over four, rounded up, so empty text
        costs nothing and any other text at least one token."""
        ...

    def chars(self, tokens: int) -> int:
        """The most characters `tokens` estimated tokens may hold: four for each."""
        ...
