# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The arithmetic of "how long until this machine needs replacing", kept apart and tested.

A health driver (battery capacity, SSD wear, generation rate, free disk) is a weekly series.
It is fitted with the Theil-Sen estimator: the slope is the median of every pairwise slope,
so one odd week (a reboot mid-benchmark, a log rotation) cannot drag it, and the intercept
is the median residual. Its interval is Sen's: rank-based, from the variance of Kendall's
S, so it needs nothing beyond the normal quantile the standard library has.

    slopes      = sorted((y_j - y_i) / (x_j - x_i) for i < j, x_j != x_i)
    C           = z_(1+conf)/2 * sqrt(n (n - 1) (2n + 5) / 18)
    slope_low   = the round((N - C) / 2)-th slope   (N = len(slopes); -inf if below 1)
    slope_high  = the round((N + C) / 2 + 1)-th     (+inf if beyond N)

The projected crossing is where the line through the anchor (the median x and the fitted
value there) reaches the threshold: the central slope gives the central date, the steeper
adverse bound the earliest, the shallower one the latest -- and when the shallower bound is
not adverse at all (it points away from the threshold), the latest is unbounded: the data
cannot rule out "never". A central slope that is not adverse is "not approaching".

Stdlib only, like the script that uses it, so it runs under `uv run --no-project`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist, median

try:
    from scripts.interfaces.host_health_forecast_interface import (
        ThresholdProjectorInterface,
        TrendEstimatorInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.host_health_forecast_interface import (  # type: ignore[import-not-found,no-redef]
        ThresholdProjectorInterface,
        TrendEstimatorInterface,
    )

DIRECTIONS = ("rising", "falling")


@dataclass(frozen=True)
class TrendFit:
    """A robust line and the interval on its slope."""

    slope: float
    intercept: float
    slope_low: float
    slope_high: float
    n: int
    x_anchor: float
    y_anchor: float
    confidence: float

    def at(self, x: float) -> float:
        return self.intercept + self.slope * x


@dataclass(frozen=True)
class Crossing:
    """Where a trend meets a threshold, in the fit's own x units (days, here).

    `approaching` is False when the central slope points away from the threshold; then
    every date is None. `latest` is None when the interval cannot rule out "never".
    """

    approaching: bool
    central: float | None
    earliest: float | None
    latest: float | None


class TheilSenEstimator(TrendEstimatorInterface):
    """The Theil-Sen slope with Sen's (1968) rank-based confidence interval."""

    def __init__(self, confidence: float) -> None:
        if not 0 < confidence < 1:
            raise ValueError(f"confidence must be in (0, 1), not {confidence}")
        self.confidence = confidence

    def fit(self, xs: Sequence[float], ys: Sequence[float]) -> TrendFit:
        if len(xs) != len(ys):
            raise ValueError("xs and ys differ in length")
        slopes = sorted(
            (ys[j] - ys[i]) / (xs[j] - xs[i])
            for i in range(len(xs))
            for j in range(i + 1, len(xs))
            if xs[j] != xs[i]
        )
        if not slopes:
            raise ValueError("a trend needs at least two points at different times")
        n = len(xs)
        slope = median(slopes)
        intercept = median(y - slope * x for x, y in zip(xs, ys, strict=True))
        low, high = self.interval(slopes, n)
        x_anchor = median(xs)
        return TrendFit(
            slope=slope,
            intercept=intercept,
            slope_low=low,
            slope_high=high,
            n=n,
            x_anchor=x_anchor,
            y_anchor=intercept + slope * x_anchor,
            confidence=self.confidence,
        )

    def interval(self, slopes: Sequence[float], n: int) -> tuple[float, float]:
        """Sen's interval on the slope, from the variance of Kendall's S (no tie correction)."""
        count = len(slopes)
        z = NormalDist().inv_cdf((1 + self.confidence) / 2)
        c = z * math.sqrt(n * (n - 1) * (2 * n + 5) / 18)
        lower_rank = round((count - c) / 2)
        upper_rank = round((count + c) / 2) + 1
        low = slopes[lower_rank - 1] if lower_rank >= 1 else -math.inf
        high = slopes[upper_rank - 1] if upper_rank <= count else math.inf
        return low, high


class ThresholdProjector(ThresholdProjectorInterface):
    """When a fitted trend reaches a threshold, with the interval its slope allows."""

    def crossing(self, fit: TrendFit, threshold: float, direction: str) -> Crossing:
        if direction not in DIRECTIONS:
            raise ValueError(f"direction must be one of {DIRECTIONS}, not {direction!r}")
        sign = 1.0 if direction == "rising" else -1.0
        if not sign * fit.slope > 0:
            return Crossing(approaching=False, central=None, earliest=None, latest=None)
        central = self._through_anchor(fit, threshold, fit.slope)
        # The adverse bound with the larger magnitude reaches the threshold first.
        steep, shallow = (
            (fit.slope_high, fit.slope_low) if sign > 0 else (fit.slope_low, fit.slope_high)
        )
        earliest = self._through_anchor(fit, threshold, steep) if sign * steep > 0 else None
        latest = self._through_anchor(fit, threshold, shallow) if sign * shallow > 0 else None
        if earliest is None or (central is not None and earliest > central):
            earliest = central
        return Crossing(approaching=True, central=central, earliest=earliest, latest=latest)

    @staticmethod
    def _through_anchor(fit: TrendFit, threshold: float, slope: float) -> float | None:
        if math.isinf(slope):
            return fit.x_anchor
        return fit.x_anchor + (threshold - fit.y_anchor) / slope
