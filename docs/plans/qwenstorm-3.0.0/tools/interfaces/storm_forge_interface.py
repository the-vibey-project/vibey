"""What the forge promises the storm's tools, declared beside `storm_forge.py` (sub-doctrine 9.b).

Declares; never consumes. It imports the standard library and nothing of its own tree, and
`tests/meta/test_storm_ledger.py` holds both the class and the tests' double to it, so the
declaration cannot drift from what either implements.

`lane-publish.py` and `lane-reap.py` take this, not the class: the composition happens in
each tool's entry point, and a test hands them a double instead of patching `subprocess`.
The two value types the contract speaks in are declared here too, because a caller has to be
able to name what it receives without importing the implementation.
"""

from __future__ import annotations

from typing import NamedTuple, Protocol, runtime_checkable


class Unreadable(RuntimeError):
    """The forge could not be read completely, so nothing may be concluded from it."""


class PullRequest(NamedTuple):
    """One pull request, and the issues its body closes by the forge's own grammar."""

    number: int
    state: str  # OPEN, MERGED or CLOSED, as the forge spells them
    head: str
    closes: frozenset[int]


@runtime_checkable
class StormForgeInterface(Protocol):
    """The forge's pull requests, and what each one says it closes."""

    def pull_requests(self) -> list[PullRequest]:
        """Every pull request, newest first; raises `Unreadable` rather than guess."""
        ...

    def closes(self, body: str | None) -> frozenset[int]:
        """The issue numbers a pull request body closes."""
        ...

    def closing(self, prs: list[PullRequest], issue: int | None) -> list[PullRequest]:
        """The pull requests in `prs` that close `issue`, in the order given."""
        ...

    def heads(self, prs: list[PullRequest]) -> dict[str, tuple[int, str]]:
        """Each head ref's newest pull request, as (number, state)."""
        ...
