# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for turning what already ran into a graded prediction (ADR-0016).

There is exactly ONE estimator in this family (ADR-0017; #88, #134): the fit calculus
fits its service time through it, `vibey-gh estimate` projects durations through it, and
the vibey-side forecast that reads phase timings from the ledger is meant to take the
same seam rather than grow a second least-squares of its own.

The records it speaks in -- `Sample`, `LinearFit`, `Prediction`, `Grade`, `TrackRecord`
-- are imported for typing only. They are frozen data, the same standing `Machine` has in
the memory seam: naming the shape a seam speaks in is declaring, not consuming.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.estimation import Grade, LinearFit, Prediction, Sample, TrackRecord


@runtime_checkable
class GradedEstimatorInterface(Protocol):
    """Observations in; a prediction with its basis out; later, that prediction graded."""

    def fit(self, samples: Sequence[Sample]) -> LinearFit:
        """The line `y = intercept + slope * x` the samples support, and which basis it
        rests on -- a least-squares fit, a flat mean when the slope cannot be identified or
        would be physically meaningless, or nothing at all when there are no samples."""
        ...

    def predict(self, samples: Sequence[Sample], x: float = 0.0) -> Prediction:
        """The outcome expected at `x`, carrying its basis and how many samples stand
        behind it. With no samples the value is `None` -- unknown, never zero."""
        ...

    def grade(self, prediction: Prediction, actual: float) -> Grade:
        """What the prediction said beside what actually happened, and the error between
        them. A prediction that had no value is recorded as ungraded, not as a miss."""
        ...

    def track_record(self, grades: Sequence[Grade]) -> TrackRecord:
        """How the estimator has done on record: its bias and its typical error, over the
        grades that had a prediction to judge."""
        ...
