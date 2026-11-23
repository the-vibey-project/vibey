# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over a run input's digest and the names a run input may have (SP-LOOPS Phase 3).

Implemented by `domain/run_input.py`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.run_input import RunInput


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

    def name_digest(self, name: str) -> str:
        """The SHA-256 of a run input's name, as the ledger records it beside the digest: the
        ledger holds no name, and this lets a row under another name be told apart."""
        ...

    def row_of(self, line: bytes) -> RunInput | None:
        """One index row (a JSON object: digest, kind, name, size, and anything else) as the run
        input it records, or None when it is not one a store writes: not JSON or not UTF-8, not
        an object, a digest that is not one, a kind that is not `paste` or `file`, a name this
        rule refuses, or a size that is not a non-negative integer. Every store reads its index
        through this one rule, so a row a local store skips a network store skips too."""
        ...
