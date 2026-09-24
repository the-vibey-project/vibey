# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam that turns two lanes' answers into the one review verdict the gate reads.

Once the sovereign lane carries the diff-groundable half of a review and the paid lane the
rest (doctrine 8.a, #133), no single reviewer's answer is the verdict any more. Something
has to put the halves back together, decide the one pass/fail the gate publishes, and say
which lane carried which field. This declares that thing; `vibey_gh.review_composition`
supplies the one the workflow calls through `vibey-gh pr-automation combine`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ReviewComposerPort(Protocol):
    """Composes one review verdict from the lane or lanes that answered it."""

    def compose(
        self,
        paid: Mapping[str, Any] | None,
        *,
        half: str,
        sovereign: Mapping[str, Any] | None = None,
        head_sha: str = "",
    ) -> dict[str, Any]:
        """The composed review for one exact head.

        `half` names what the PAID reviewer answered: the full schema; only the
        requires-wider-context half, in which case `sovereign` must be the sovereign lane's
        verdict for the diff-groundable half; or nothing at all, because no paid review is
        declared (8.b), in which case `paid` is empty and `sovereign` must be a verdict that
        answered both halves. Returns the envelope the workflow reads: the verdict to
        persist, what repair is handed, the field-to-lane map, each unit's outcome, the
        findings count and whether automated repair may act on the result. Raises
        `ValueError` for an unknown half, a missing answer, or a sovereign verdict that
        cannot stand for the review asked of it, and `TypeError` for an answer that is not
        a JSON object.
        """


@runtime_checkable
class ReviewComposerInterface(ReviewComposerPort, Protocol):
    """The concrete two-lane review composer."""

    def compose(
        self,
        paid: Mapping[str, Any] | None,
        *,
        half: str,
        sovereign: Mapping[str, Any] | None = None,
        head_sha: str = "",
    ) -> dict[str, Any]: ...
