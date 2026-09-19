# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The graded estimator: observations in, a prediction with its basis out, then a grade.

One estimator, shared (ADR-0017). Two issues asked for the same thing from opposite ends:
#134 wants `vibey-gh estimate` to say how long an operation will take, and #88 wants
time-to-launch predicted from the conductor's own phase timings, "each prediction stored
beside the eventual actual so the estimator is graded on record". The fit calculus
(#263) already had the arithmetic, private to one function. This module is that
arithmetic lifted out whole, so the fit, the operation estimate, and the vibey-side
forecast all predict -- and are graded -- the same way. Never two estimators.

The shape is deliberately small:

- a **sample** is one thing that actually ran: a feature it scales with (`x`, e.g. a
  payload in KB, or 0 when there is none) and the outcome that was measured (`y`);
- the **fit** is `y = intercept + slope * x` by least squares, with two honest refusals
  carried over from the fit calculus unchanged. One distinct `x` cannot separate the two
  terms, so it all goes to the intercept and the slope stays zero rather than being
  invented. And a negative term -- a bigger payload finishing sooner -- is physically
  meaningless for a duration or a cost, so it falls back to the flat mean;
- a **prediction** is the fit read at one `x`, carrying its basis and `n`. With no samples
  its value is `None`: unknown, never a zero that reads like a measurement (doctrine 10);
- a **grade** sets a prediction beside the actual that later happened, and a **track
  record** summarises the grades. Nothing here decides what to do about a bad record; it
  only makes the record exist.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from vibey_gh.interfaces.graded_estimator_interface import GradedEstimatorInterface

__all__ = [
    "BASIS_LINEAR",
    "BASIS_MEAN",
    "BASIS_NONE",
    "Grade",
    "GradedEstimator",
    "LinearFit",
    "Prediction",
    "Sample",
    "TrackRecord",
]

# Which evidence a prediction rests on. Strings rather than an enum for the same reason the
# fit's verdicts are (`admit`, `defer`, `floor`): they are written into journals and JSON,
# and a reader months later should not need this module to know what they say.
BASIS_LINEAR = "linear"  # least squares over two or more distinct x
BASIS_MEAN = "mean"  # the flat mean: one distinct x, or a refused negative fit
BASIS_NONE = "none"  # no samples at all -- nothing is predicted

_NO_SAMPLES = "no samples: nothing has been measured, so nothing is predicted"
_ONE_X = "one distinct x: the slope cannot be separated from the intercept, so it stays zero"
_NEGATIVE = "a negative term is physically meaningless here, so the flat mean stands instead"
_LEAST_SQUARES = "least squares over the samples"


@dataclass(frozen=True)
class Sample:
    """One thing that actually ran: the feature it scales with, and what it measured."""

    x: float
    y: float


@dataclass(frozen=True)
class LinearFit:
    """`y = intercept + slope * x`, with the basis it rests on and the samples behind it."""

    intercept: float
    slope: float
    n: int
    basis: str
    reason: str

    def at(self, x: float) -> float:
        """The line read at `x`. Meaningful only when `n > 0`; see `Prediction`."""
        return self.intercept + self.slope * x


@dataclass(frozen=True)
class Prediction:
    """What the estimator expects at `x`, and exactly what that expectation rests on."""

    value: float | None
    x: float
    basis: str
    n: int
    reason: str

    @property
    def known(self) -> bool:
        return self.value is not None


@dataclass(frozen=True)
class Grade:
    """A prediction set beside the actual that later happened.

    `error` is `actual - predicted`: positive when the estimator under-predicted, which is
    the direction that misses deadlines and budgets. A prediction that had no value cannot
    be wrong, so its error is `None` and it is counted as ungraded rather than as a miss.
    """

    predicted: float | None
    actual: float
    basis: str
    n: int

    @property
    def error(self) -> float | None:
        return None if self.predicted is None else self.actual - self.predicted

    @property
    def abs_error(self) -> float | None:
        error = self.error
        return None if error is None else abs(error)

    @property
    def relative_error(self) -> float | None:
        """`error / actual`, or `None` when there is no error or nothing to divide by."""
        error = self.error
        if error is None or self.actual == 0:
            return None
        return error / self.actual


@dataclass(frozen=True)
class TrackRecord:
    """How an estimator has done on record, over the grades that had something to judge."""

    graded: int
    ungraded: int
    mean_error: float | None
    mean_abs_error: float | None


class GradedEstimator(GradedEstimatorInterface):
    """The one estimator: least squares with the fit calculus's refusals, then grading.

    `nonnegative` keeps the refusal of negative fits, and is on by default because every
    quantity this family estimates -- a duration, a cost -- cannot go below zero. A caller
    estimating something that legitimately can passes `False` (ADR-0018).
    """

    def __init__(self, *, nonnegative: bool = True) -> None:
        self._nonnegative = nonnegative

    def fit(self, samples: Sequence[Sample]) -> LinearFit:
        # The arithmetic below is `vibey_gh.fit.estimate_from`'s, moved rather than
        # rewritten: the same sums in the same order, so the fit calculus that now wraps
        # this gets bit-identical constants (test_estimation pins it against a verbatim
        # copy of the original).
        if not samples:
            return LinearFit(intercept=0.0, slope=0.0, n=0, basis=BASIS_NONE, reason=_NO_SAMPLES)
        xs = [s.x for s in samples]
        ys = [s.y for s in samples]
        n = len(samples)
        mean_x = sum(xs) / n
        mean_y = sum(ys) / n
        var_x = sum((x - mean_x) ** 2 for x in xs)
        if var_x > 0:
            slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
            intercept = mean_y - slope * mean_x
            basis, reason = BASIS_LINEAR, _LEAST_SQUARES
        else:
            slope, intercept = 0.0, mean_y
            basis, reason = BASIS_MEAN, _ONE_X
        if self._nonnegative and (intercept < 0 or slope < 0):
            slope, intercept = 0.0, mean_y
            basis, reason = BASIS_MEAN, _NEGATIVE
        return LinearFit(intercept=intercept, slope=slope, n=n, basis=basis, reason=reason)

    def predict(self, samples: Sequence[Sample], x: float = 0.0) -> Prediction:
        line = self.fit(samples)
        value = line.at(x) if line.n else None
        return Prediction(value=value, x=x, basis=line.basis, n=line.n, reason=line.reason)

    def grade(self, prediction: Prediction, actual: float) -> Grade:
        return Grade(
            predicted=prediction.value, actual=actual, basis=prediction.basis, n=prediction.n
        )

    def track_record(self, grades: Sequence[Grade]) -> TrackRecord:
        errors = [g.error for g in grades if g.error is not None]
        if not errors:
            return TrackRecord(graded=0, ungraded=len(grades), mean_error=None, mean_abs_error=None)
        return TrackRecord(
            graded=len(errors),
            ungraded=len(grades) - len(errors),
            mean_error=sum(errors) / len(errors),
            mean_abs_error=sum(abs(e) for e in errors) / len(errors),
        )
