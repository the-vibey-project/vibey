# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/host_health_forecast.py`: the fit recovers known parameters from synthetic
series, its interval covers them, an odd week cannot drag it, and the projection says
"not approaching" and "not bounded" when the data says so.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import math
import random

import pytest

from scripts.host_health_forecast import (
    Crossing,
    TheilSenEstimator,
    ThresholdProjector,
    TrendFit,
)
from scripts.interfaces import host_health_forecast_interface as contracts


def series(
    a: float, b: float, n: int, noise: float, seed: int = 7
) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    xs = [7.0 * i for i in range(n)]
    return xs, [a + b * x + rng.gauss(0, noise) for x in xs]


def test_the_classes_satisfy_their_contracts() -> None:
    assert contracts.TrendEstimatorInterface in TheilSenEstimator.__mro__
    assert contracts.ThresholdProjectorInterface in ThresholdProjector.__mro__


def test_an_exact_line_is_recovered_exactly() -> None:
    fit = TheilSenEstimator(0.9).fit([0, 7, 14, 21, 28], [1.0, 0.93, 0.86, 0.79, 0.72])
    assert fit.slope == pytest.approx(-0.01)
    assert fit.intercept == pytest.approx(1.0)
    assert fit.at(14) == pytest.approx(0.86)
    assert fit.n == 5


@pytest.mark.parametrize(("a", "b"), [(1.0, -0.0004), (25.0, -0.02), (3.0, 0.15)])
def test_a_noisy_line_is_recovered_and_its_interval_covers_the_true_slope(
    a: float, b: float
) -> None:
    xs, ys = series(a, b, n=40, noise=abs(b) * 7 * 0.5)
    fit = TheilSenEstimator(0.95).fit(xs, ys)
    assert fit.slope == pytest.approx(b, rel=0.15)
    assert fit.slope_low <= b <= fit.slope_high
    assert fit.slope_low < fit.slope < fit.slope_high


def test_one_odd_week_does_not_drag_the_slope() -> None:
    xs, ys = series(25.0, -0.02, n=20, noise=0.05)
    ys[10] = 2.0  # a reboot mid-benchmark
    robust = TheilSenEstimator(0.9).fit(xs, ys)
    assert robust.slope == pytest.approx(-0.02, rel=0.1)


def test_the_projection_recovers_a_known_crossing_and_brackets_it() -> None:
    # Battery capacity falling 0.2 points of ratio a year: from 1.0 it reaches 0.8 at day 365.
    b = -0.2 / 365
    xs, ys = series(1.0, b, n=26, noise=0.002)
    fit = TheilSenEstimator(0.9).fit(xs, ys)
    crossing = ThresholdProjector().crossing(fit, 0.8, "falling")
    assert crossing.approaching
    assert crossing.central == pytest.approx(365, rel=0.08)
    assert crossing.earliest is not None and crossing.latest is not None
    assert crossing.earliest <= crossing.central <= crossing.latest
    assert crossing.earliest <= 365 <= crossing.latest


def test_a_rising_driver_projects_forward() -> None:
    fit = TheilSenEstimator(0.9).fit([0, 7, 14, 21, 28, 35], [10, 11, 12, 13, 14, 15])
    crossing = ThresholdProjector().crossing(fit, 100, "rising")
    assert crossing.central == pytest.approx(630)


def test_a_trend_moving_away_is_not_approaching() -> None:
    fit = TheilSenEstimator(0.9).fit([0, 7, 14, 21], [10, 11, 12, 13])
    assert ThresholdProjector().crossing(fit, 5, "falling") == Crossing(False, None, None, None)


def test_an_interval_that_allows_never_leaves_the_latest_unbounded() -> None:
    # Nearly flat and noisy: the slope is adverse, but its upper bound is not.
    fit = TrendFit(
        slope=-0.001,
        intercept=1.0,
        slope_low=-0.003,
        slope_high=0.002,
        n=6,
        x_anchor=17.5,
        y_anchor=0.98,
        confidence=0.9,
    )
    crossing = ThresholdProjector().crossing(fit, 0.8, "falling")
    assert crossing.approaching and crossing.latest is None
    assert crossing.earliest is not None and crossing.earliest < crossing.central  # type: ignore[operator]


def test_few_points_widen_the_interval_to_infinity() -> None:
    fit = TheilSenEstimator(0.9).fit([0, 7, 14], [1.0, 0.99, 0.98])
    assert fit.slope_low == -math.inf and fit.slope_high == math.inf
    crossing = ThresholdProjector().crossing(fit, 0.8, "falling")
    # An infinitely steep bound reaches the threshold at the anchor: "cannot rule out now".
    assert crossing.earliest == fit.x_anchor
    assert crossing.latest is None


def test_bad_input_is_refused() -> None:
    with pytest.raises(ValueError, match="confidence"):
        TheilSenEstimator(1.0)
    with pytest.raises(ValueError, match="differ in length"):
        TheilSenEstimator(0.9).fit([1, 2], [1])
    with pytest.raises(ValueError, match="two points"):
        TheilSenEstimator(0.9).fit([3, 3], [1, 2])
    fit = TheilSenEstimator(0.9).fit([0, 1], [0, 1])
    with pytest.raises(ValueError, match="direction"):
        ThresholdProjector().crossing(fit, 1, "sideways")
