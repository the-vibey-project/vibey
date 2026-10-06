# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams that record how long each request to a local model took, and report it.

The sovereign review either answered in minutes or gave no verdict after two and a half
hours, and its per-request deadline was scaled from rates measured on the operator's host,
not on the runner that serves the model. Nothing recorded what each request actually sent,
how long it was given, how long it took, or what the model's own counters said. These
declare the log a review writes those facts into -- one entry per request attempt, and one
per slot probe -- and the read-only report that turns a set of outcome records into the
rates a runner was observed to sustain. `vibey_gh.review_timings` supplies all of them.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RequestLogInterface(Protocol):
    """Every request one review made of a local model, in the order it made them."""

    def part(self, index: int, count: int) -> None:
        """Requests from here on are for part `index` of `count`; the attempt count starts
        again. A review that is not chunked is part 1 of 1."""
        ...

    def attempt(self) -> int:
        """Start the next attempt of the current part, and return its number, from 1."""
        ...

    def open(self, kind: str, **fields: Any) -> int:
        """Record that a request of `kind` (`request`, or `slot_probe` for the one-token
        request that waits for the model to come free) has started, with `fields`; stamped
        with the current part and attempt and the seconds since the review began. Returns
        the entry's index, for `close`. Until closed, the entry says it is unfinished."""
        ...

    def close(self, index: int, **fields: Any) -> None:
        """Record that the request at `index` has ended, with `fields` and the seconds it
        took."""
        ...

    def entries(self) -> list[dict[str, Any]]:
        """Every entry so far, as JSON-ready dictionaries, oldest first."""
        ...

    def figures(self, body: object) -> dict[str, Any] | None:
        """Ollama's own counters from a reply body -- tokens read and written, and the
        nanosecond durations, as seconds -- with the rates they imply; None when `body` is
        not a reply. Never raises on a malformed body."""
        ...


@runtime_checkable
class RunnerLabelInterface(Protocol):
    """Which runner a review ran on, as the runner's own environment states it."""

    @property
    def environment(self) -> str:
        """`RUNNER_ENVIRONMENT`: `github-hosted` or `self-hosted`; empty when unstated."""
        ...

    @property
    def os(self) -> str:
        """`RUNNER_OS`; empty when unstated."""
        ...

    @property
    def arch(self) -> str:
        """`RUNNER_ARCH`; empty when unstated."""
        ...

    @property
    def name(self) -> str:
        """`RUNNER_NAME`; empty when unstated. Unique per machine on a hosted runner."""
        ...

    def as_json(self) -> dict[str, str]:
        """The fields that were stated, and only those."""
        ...

    def describe(self, *, with_name: bool = False) -> str:
        """The label in words, for a person; says so when nothing was stated."""
        ...


@runtime_checkable
class TimingsGroupInterface(Protocol):
    """The requests one model made on one kind of runner, and the rates they show."""

    def observed(self) -> list[Mapping[str, Any]]:
        """Every finished review request the model answered with both of its rates."""
        ...

    def timed_out(self) -> list[dict[str, Any]]:
        """Every review request that ran out of time -- its estimated prompt tokens, its
        deadline and how long it ran -- smallest prompt first."""
        ...

    def suggestion(self) -> dict[str, Any]:
        """The rates a deadline could conservatively be scaled from, and from how many
        observations; none at all below the group's minimum."""
        ...

    def as_json(self) -> dict[str, Any]:
        """Everything the group shows, for a program."""
        ...

    def render(self) -> list[str]:
        """Everything the group shows, a line each, for a person."""
        ...


@runtime_checkable
class TimingsReportInterface(Protocol):
    """The observed request timings of a set of outcome records, grouped by model and runner."""

    def as_json(self) -> dict[str, Any]:
        """The whole report, every group and every file skipped, for a program."""
        ...

    def render(self) -> str:
        """The report for a person: what was read, and when, first."""
        ...


@runtime_checkable
class ReviewTimingsInterface(Protocol):
    """Reads `vibey-gh local-review --outcome` records and reports their request timings.
    Read-only: it never writes anything."""

    def records(
        self, paths: Sequence[Path]
    ) -> tuple[list[tuple[str, Mapping[str, Any]]], list[tuple[str, str]]]:
        """`(read, skipped)`: every local-review outcome record under `paths` -- each a file,
        or a directory searched recursively for `*.json` -- by path, and every file that was
        not one, by path with the reason. A file that cannot be read, or is not a local-review
        record, is skipped and named, never guessed at."""
        ...

    def report(self, paths: Sequence[Path]) -> TimingsReportInterface:
        """The timings of every record under `paths`, grouped, with every skip named."""
        ...
