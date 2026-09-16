# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam a reviewer reads its own remit from.

Two reviewers answer vibey-gh's review schema from different evidence -- the paid
exact-head reviewer sees the whole proposed repository, the local fallback sees one diff.
Each needs to know which judgments its evidence supports, and neither should own that
answer. This declares the shape of the thing that holds it; `vibey_gh.review_contract`
supplies the one this repository uses.
"""

from __future__ import annotations

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
