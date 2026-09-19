# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for estimating one operation before it runs (#134; ADR-0016).

Before a run starts, whoever launches it is told -- in numbers where numbers exist and
in the word `unknown` where they do not -- whether it can complete through every stage it
must pass, how long it will take, what it will cost, and how far each coordinate of the
state sits from peak.

`OperationEstimate` is imported for typing only -- a frozen record, the same standing
`Machine` has in the memory seam.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.estimate_report import OperationEstimate


@runtime_checkable
class OperationEstimatorInterface(Protocol):
    """Measures what it can, judges the path, and says what it could not measure."""

    def estimate(
        self, operation: str, *, start: str | None = None, payload_bytes: int = ...
    ) -> OperationEstimate:
        """The estimate for a run from `start` (the first stage when omitted) through the
        stage `operation`, with the local model's service time projected for a payload of
        `payload_bytes` (the implementation's default when omitted). A stage that does not
        exist is a `ValueError` naming the ones that do; nothing is measured, and nothing
        invented, for a path that is not one."""
        ...
