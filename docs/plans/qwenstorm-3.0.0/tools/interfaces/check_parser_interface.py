"""What the check parser promises, declared beside `check_parser.py` (ADR-0016, sub-doctrine 9.b).

Declares; never consumes. It imports the standard library only.
`tests/meta/test_storm_check_parser.py` holds `CheckParser` to it method by method and
parameter by parameter, so the declaration cannot drift from the class.

The checks it returns are `check_parser.Check` values; they are typed `Any` here because an
interface does not import the implementation it describes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CheckParserInterface(Protocol):
    """Every line of a spec's check block is run, classified, or reported -- never skipped."""

    def block_of(self, text: str) -> str | None:
        """The check block of a spec or a lane's issue.md, or None when it has none."""
        ...

    def parse_checks(self, text: str, lane: Path) -> tuple[list[Any], list[tuple[str, str]]]:
        """The checks that can run, and every line that cannot, with the reason why."""
        ...

    def tokens(self, command: str) -> list[str]:
        """A command split as a shell splits it, unquoted parentheses as tokens of their own."""
        ...

    def expand(self, value: str, known: dict[str, str]) -> str | None:
        """An assignment's value as a shell would expand it, or None if it cannot be."""
        ...

    def assigned(self, parts: list[str], env: dict[str, str]) -> tuple[list[str], str | None]:
        """Consume leading `NAME=value` words into `env`: what is left, or why it cannot run."""
        ...

    def where(self, lane: Path, raw: str) -> Path:
        """The directory a check runs in: the lane, or the tenant its line names."""
        ...

    def inside(self, lane: Path, base: Path, target: str) -> Path | None:
        """`base/target`, or None when that is not a real directory within the lane."""
        ...
