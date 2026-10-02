# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/host_health_forecast.py` implements. Interfaces declare; they never consume.

A *trend estimator* fits a line to a weekly series with an honest interval on its slope. A
*threshold projector* says when that line reaches a replacement threshold: a central date
and the earliest and latest the interval allows, or that it is not approaching at all.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class TrendEstimatorInterface(Protocol):
    """Fits y = intercept + slope * x robustly, with a confidence interval on the slope."""

    def fit(self, xs: Sequence[float], ys: Sequence[float]) -> Any:
        """A fit carrying slope, intercept, slope_low, slope_high, n and its anchor point."""
        ...


class ThresholdProjectorInterface(Protocol):
    """Projects a fitted trend onto a threshold."""

    def crossing(self, fit: Any, threshold: float, direction: str) -> Any:
        """When the trend reaches `threshold`, worsening in `direction` (rising/falling)."""
        ...
