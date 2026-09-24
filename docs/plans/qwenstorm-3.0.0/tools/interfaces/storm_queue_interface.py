"""What the storm's queue and priority lane promise, declared beside `storm_queue.py`.

ADR-0016 and sub-doctrine 9.b; the contract itself is ADR-0054. Declares; never consumes.
`tests/meta/test_storm_priority.py` holds each class to its declaration here, method by
method and parameter by parameter, so the two cannot drift.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NamesInterface(Protocol):
    """What a slug, dependency or source may be, and how outside text is written."""

    def valid(self, value: object) -> bool:
        """True for `[A-Za-z0-9][A-Za-z0-9._-]*` with no `..`, and short enough."""
        ...

    def check(self, value: str, what: str) -> None:
        """`Invalid` unless `value` is valid."""
        ...

    def quote(self, value: object) -> str:
        """Outside text as one printable, escaped JSON string."""
        ...

    def printable(self, text: str) -> str:
        """`text` with every non-printable character escaped: always one line."""
        ...


@runtime_checkable
class QueueFileInterface(Protocol):
    """`queue.txt`: `<slug> <issue> [dep1,dep2,...]`, one lane per line."""

    path: Path

    def entries(self) -> list[Any]:
        """Every entry in file order; a slug listed twice keeps its first line."""
        ...

    def append(self, entry: Any) -> None:
        """Append one whole line, even onto a file with no final newline."""
        ...


@runtime_checkable
class LedgerInterface(Protocol):
    """The storm's settled and finished state, and the records the queue writes."""

    root: Path

    def integrated(self) -> frozenset[str]:
        """Every slug in `integrated.txt`."""
        ...

    def abandoned(self) -> frozenset[str]:
        """Every slug in `abandoned.txt`."""
        ...

    def finished(self, slug: str) -> bool:
        """True when the lane has a `result.json` -- it ran and awaits review."""
        ...

    def unattended(self) -> bool:
        """True when finished lanes wait for a batch review instead of holding the storm."""
        ...

    def block(self, entry: Any, dep: str) -> None:
        """Mark a lane blocked on an abandoned dependency, visibly."""
        ...

    def say(self, message: str) -> None:
        """Append one stamped, plain-words line to `progress.log`, control characters escaped."""
        ...

    def say_once(self, message: str) -> None:
        """`say`, unless the same words are already in the log's recent tail."""
        ...


@runtime_checkable
class PriorityLogInterface(Protocol):
    """The append-only priority log, whose replay is the priority lane."""

    path: Path

    def events(self) -> list[dict[str, Any]]:
        """Every event in order, or `Unreadable` when any line cannot be read."""
        ...

    def replay(self) -> list[str]:
        """The priority lane: the slugs the log prioritises, first pushed first."""
        ...

    def append(self, event: dict[str, Any]) -> None:
        """Append one event, durably, never editing an earlier line."""
        ...

    def existed(self) -> bool:
        """True when the lock file or the evidence watermark says the log was written."""
        ...

    def locked(self) -> AbstractContextManager[None] | Iterator[None]:
        """Held while one change reads the order and records itself."""
        ...


@runtime_checkable
class AuthorityInterface(Protocol):
    """Who may change the priority lane: the operator, or a declared source."""

    sources: tuple[str, ...]

    def authorise(self, source: str | None) -> str:
        """The principal a change is recorded under, or `Unauthorised`."""
        ...

    def describe(self, source: str | None) -> str:
        """Who the caller claims to be, for recording a request that was not authorised."""
        ...


@runtime_checkable
class PriorityLogsInterface(Protocol):
    """Finds a storm's priority log and the witnesses that it existed."""

    def at(self, root: Path) -> PriorityLogInterface:
        """The priority log for the storm at `root`."""
        ...


@runtime_checkable
class ResolverInterface(Protocol):
    """What runs next: the priority lane first, then `queue.txt`."""

    def order(self) -> list[tuple[Any, bool]]:
        """Every queued entry in the order the storm considers them, and whether prioritised."""
        ...

    def plan(self) -> Any:
        """The effective order and the decision, writing nothing."""
        ...

    def next(self) -> str:
        """The decision the runner acts on, after marking blocked lanes as the runner did."""
        ...


@runtime_checkable
class PriorityDeskInterface(Protocol):
    """Push, bump and un-bump: authorised, validated, recorded, reported."""

    def push(self, slug: str, issue: str, deps: Sequence[str], source: str | None) -> list[str]:
        """Prioritise `slug`, appending it to `queue.txt` first when it is new."""
        ...

    def bump(self, slug: str, source: str | None) -> list[str]:
        """Prioritise a lane `queue.txt` already carries."""
        ...

    def unbump(self, slug: str, source: str | None) -> list[str]:
        """Return `slug` to its `queue.txt` position."""
        ...


@runtime_checkable
class PriorityCliInterface(Protocol):
    """`storm-priority.py`: push, bump, unbump and list, with the documented exit codes."""

    def parser(self) -> argparse.ArgumentParser:
        """The command line."""
        ...

    def run(self, argv: list[str]) -> int:
        """Carry out one command; 0 done, 1 and 2 refused, 3 order unknown, 4 crashed."""
        ...

    def show(self) -> int:
        """Print the order the storm will run."""
        ...
