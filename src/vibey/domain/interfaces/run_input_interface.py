# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a run input's digest and the names a run input may have (SP-LOOPS Phase 3).

Implemented by `domain/run_input.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class RunInputRuleInterface(Protocol):
    def digest_of(self, data: bytes) -> str:
        """The lowercase hex SHA-256 of `data`: the address a run input is stored under and the
        only thing about its content the ledger records."""
        ...

    def valid_name(self, name: str, *, max_bytes: int = 255) -> str | None:
        """None when `name` may name a run input; else the reason it is refused: empty, `.` or
        `..`, a `/` or `\\`, a NUL, text that cannot be written as UTF-8, or more than
        `max_bytes` UTF-8 bytes."""
        ...

    def is_digest(self, text: str) -> bool:
        """Whether `text` is a digest this rule makes: exactly 64 lowercase hex digits."""
        ...
