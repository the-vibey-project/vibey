# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams that say, in a closed vocabulary, why a review did or did not produce a verdict.

`PR review / gate` used to explain itself only in prose: a sentence in a check run, a line
in a job log. Nobody could count why reviews were skipped, because every reason was worded
where it happened. These declare the vocabulary every lane decision and every no-verdict
reason is recorded in, and the read-only reader that tabulates those records over the last
runs of the review workflow. `vibey_gh.review_outcome` supplies both.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OutcomeVocabularyInterface(Protocol):
    """The closed set of lane decisions, verdicts and outcome codes, each described."""

    @property
    def lanes(self) -> Mapping[str, str]:
        """Every lane decision, mapped to what it means."""
        ...

    @property
    def verdicts(self) -> tuple[str, ...]:
        """Every verdict a record may carry: a pass, a failure, or none at all."""
        ...

    @property
    def codes(self) -> Mapping[str, str]:
        """Every outcome code, mapped to what it means. The one place a code is defined."""
        ...

    def describe(self, code: str) -> str:
        """What `code` means, or a statement that it is not in the vocabulary -- never a
        guess at what it might have meant."""
        ...

    def problems(self, record: Mapping[str, Any]) -> list[str]:
        """Why `record` is not a well-formed review record, one line each; empty when it is.

        A code, lane or verdict outside the vocabulary is a problem, not a new category."""
        ...


@runtime_checkable
class RunRecordInterface(Protocol):
    """What one run of the review workflow recorded, and where the answer came from."""

    @property
    def run_id(self) -> int: ...

    @property
    def created_at(self) -> str: ...

    @property
    def conclusion(self) -> str:
        """The run's own conclusion as the forge reports it, or its status while running."""
        ...

    @property
    def source(self) -> str:
        """Which record answered: the gate's, the evaluation's, or why neither did --
        `none`, `expired`, `unreadable`, `in_progress`."""
        ...

    @property
    def record(self) -> Mapping[str, Any] | None: ...

    @property
    def problem(self) -> str:
        """Why the record could not be read or is not well formed; empty when it is."""
        ...


@runtime_checkable
class OutcomeTableInterface(Protocol):
    """A tabulation of review records over a stated span of runs."""

    @property
    def runs(self) -> Sequence[RunRecordInterface]: ...

    def counts(self, key: str) -> dict[str, int]:
        """How many readable records carry each value of `key` (`lane`, `code`,
        `verdict`), most frequent first."""
        ...

    def sources(self) -> dict[str, int]:
        """How many runs each source answered for, every source named, zero included."""
        ...

    def as_json(self) -> dict[str, Any]:
        """The whole table, the span it covers and every run's record, for a program."""
        ...

    def render(self) -> str:
        """The table for a person: its object, its source, its span and its cutoff first."""
        ...


@runtime_checkable
class ReviewOutcomeReaderInterface(Protocol):
    """Reads the records the review workflow left behind. Never writes anything."""

    def tabulate(self, limit: int) -> OutcomeTableInterface:
        """The records of the last `limit` runs of the review workflow, newest first."""
        ...
