# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a reviewer reads its own remit from.

Two reviewers answer vibey-gh's review schema from different evidence -- the paid
exact-head reviewer sees the whole proposed repository, the local fallback sees one diff.
Each needs to know which judgments its evidence supports, and neither should own that
answer. This declares the shape of the thing that holds it; `vibey_gh.review_contract`
supplies the one this repository uses. The same holder renders the JSON Schema a reviewer
is held to, so the halves and the schema cannot describe two different reviews.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class ReviewContractPort(Protocol):
    """States, for one review schema, which judgments a diff alone can carry."""

    @property
    def diff_groundable(self) -> tuple[str, ...]:
        """Fields a reviewer holding only the diff may answer on its own evidence."""

    @property
    def requires_wider_context(self) -> tuple[str, ...]:
        """Fields that need documents the diff does not contain."""

    @property
    def fields(self) -> tuple[str, ...]:
        """Every field the schema carries: the diff-groundable half, then the other half.

        The contract's own order, not a schema document's key order — never zipped
        positionally against one.
        """

    @property
    def unevaluated_placeholder(self) -> bool:
        """The value written for a field this reviewer did not evaluate. Not an answer."""

    @property
    def unevaluated_notice(self) -> str:
        """The sentence a diff-only verdict must carry, saying what it did not evaluate."""

    def classify(self, field: str) -> str:
        """Which half `field` belongs to. Raises `KeyError` for a field the schema lacks."""

    def is_diff_groundable(self, field: str) -> bool:
        """Whether a reviewer holding only the diff may answer `field`."""

    def placeholders(self) -> dict[str, bool]:
        """Shape-compatible values for the unevaluated fields. Never assertions."""

    @property
    def field_schemas(self) -> Mapping[str, Mapping[str, object]]:
        """The JSON Schema fragment each field is answered in, in schema key order."""

    @property
    def wider_summary_field(self) -> str:
        """Where the wider half, answered without the diff half, writes its prose."""

    @property
    def wider_findings_field(self) -> str:
        """Where the wider half, answered without the diff half, writes its findings."""

    @property
    def wider_report_fields(self) -> tuple[str, ...]:
        """The two fields above, summary first.

        Report fields rather than judgments: in neither half, never placeholdered.
        """

    @property
    def field_questions(self) -> Mapping[str, str]:
        """What each documentation judgment asks, by judgment name."""

    @property
    def scope_field(self) -> str:
        """Where a local verdict names the halves it actually answered. Never a review field."""

    def questions(self) -> list[tuple[str, str]]:
        """Each documentation judgment with its question, in the contract's order.

        Raises `KeyError` for a judgment with no declared question, as `json_schema` does
        for a field with no declared type.
        """

    def json_schema(self, halves: Iterable[str] | None = None) -> dict[str, object]:
        """The JSON Schema a reviewer answering `halves` is held to; `None` means both.

        Every selected field is required; the wider half without the diff half also
        requires `wider_report_fields`. Raises `ValueError` for an unknown half and
        `KeyError` for a selected field with no declared type.
        """


@runtime_checkable
class ReviewContractInterface(ReviewContractPort, Protocol):
    """The concrete review contract's complete field-split surface."""

    def json_schema(self, halves: Iterable[str] | None = None) -> dict[str, object]: ...
