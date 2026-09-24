"""What the storm's trust seam promises, declared beside `storm_trust.py` (ADR-0016, 9.b).

Declares; never consumes. `tests/meta/test_storm_containment.py` holds each class to its
declaration here, method by method and parameter by parameter, so the two cannot drift.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GrantInterface(Protocol):
    """`[unattended_approval]` as reviewed history states it, and where it was read."""

    source: str
    authors: tuple[str, ...]
    forbidden_paths: tuple[str, ...]


@runtime_checkable
class GrantReaderInterface(Protocol):
    """Reads the admission grant from the integration branch's reviewed state."""

    def read(self) -> GrantInterface:
        """The grant, or `Refused` when the ref or either grant file cannot be read."""
        ...

    def forbidden_touched(self, paths: Iterable[str]) -> tuple[str, ...]:
        """Which of `paths` fall under the reviewed `forbidden_paths`."""
        ...


@runtime_checkable
class ForgeInterface(Protocol):
    """Where an issue and its whole authorship history come from."""

    def issue(self, number: int) -> Any:
        """The issue as the forge reports it, or `Refused` when it cannot be read."""
        ...


@runtime_checkable
class IssueGateInterface(Protocol):
    """Admits an issue's text to a lane only if every account in its history is granted."""

    def judge(self, issue: Any, allowed: Sequence[str]) -> tuple[str | None, tuple[str, ...]]:
        """Why this issue may not direct a lane (or None), and every account in its history."""
        ...

    def admit(self, state: Path, number: int) -> str:
        """Fetch, judge and write the issue for the lane; `Refused`, recorded, otherwise."""
        ...


@runtime_checkable
class AdmissionInterface(Protocol):
    """Binds an admission record to the exact title and body bytes it admitted."""

    def digest(self, title: str, body: bytes) -> str:
        """One digest over the title and the body together."""
        ...

    def check(self, state: Path, number: int, title: str, body: bytes) -> dict[str, Any]:
        """The admission record for exactly this text, or `Refused`."""
        ...


@runtime_checkable
class PromptFenceInterface(Protocol):
    """Quotes forge text into a prompt as data, inside a fence it cannot close."""

    def nonce(self, *texts: str) -> str:
        """A random fence tag that none of `texts` contains."""
        ...

    def contain(self, record: dict[str, Any], title: str, body: str, nonce: str) -> str:
        """The fenced block, stamped with its source, author and fetch time."""
        ...
