# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/requirements_math.py`: each fit recovers what synthetic data was built from, and
each closed form agrees with the calculus it claims to solve.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import math

import pytest

from scripts.interfaces.requirements_math_interface import RequirementsMathInterface
from scripts.requirements_math import AmdahlFit, RequirementsMath

MATH = RequirementsMath()


def test_the_math_implements_its_declared_interface() -> None:
    assert RequirementsMathInterface in RequirementsMath.__mro__


def test_least_squares_recovers_an_exact_line() -> None:
    xs = [4096.0, 8192.0, 32768.0, 131072.0]
    fit = MATH.least_squares(xs, [13_000 + 0.027 * x for x in xs])
    assert fit.intercept == pytest.approx(13_000)
    assert fit.slope == pytest.approx(0.027)
    assert fit.r2 == pytest.approx(1.0)
    assert fit.max_abs_residual == pytest.approx(0, abs=1e-9)
    assert fit.solve(fit.at(50_000)) == pytest.approx(50_000)


def test_least_squares_matches_the_normal_equations_by_hand() -> None:
    # mean x = 1, mean y = 2; Sxx = 2, Sxy = 1 => b = 0.5, a = 1.5.
    # Predictions 1.5, 2.0, 2.5; residuals -0.5, 1, -0.5 => SS_res = 1.5, SS_tot = 2 => R^2 0.25.
    fit = MATH.least_squares([0, 1, 2], [1, 3, 2])
    assert (fit.intercept, fit.slope) == pytest.approx((1.5, 0.5))
    assert fit.r2 == pytest.approx(0.25)
    assert fit.residuals == pytest.approx((-0.5, 1.0, -0.5))
    assert fit.max_abs_residual == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("xs", "ys", "message"),
    [
        ([1.0], [1.0], "at least two"),
        ([1.0, 1.0], [1.0, 2.0], "same"),
        ([1.0, 2.0], [1.0], "differ in length"),
    ],
)
def test_least_squares_refuses_what_it_cannot_fit(
    xs: list[float], ys: list[float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        MATH.least_squares(xs, ys)


def test_a_flat_line_reaches_no_other_value() -> None:
    with pytest.raises(ValueError, match="flat"):
        MATH.least_squares([0, 1], [2, 2]).solve(3)


def amdahl_rates(t1: float, p: float, cores: list[int]) -> list[float]:
    return [t1 / ((1 - p) + p / n) for n in cores]


@pytest.mark.parametrize(("t1", "p"), [(0.6, 0.9), (2.0, 0.5), (1.3, 0.97)])
def test_the_amdahl_fit_recovers_known_parameters(t1: float, p: float) -> None:
    cores = [1, 2, 4, 6, 8, 10]
    fit = MATH.amdahl(cores, amdahl_rates(t1, p, cores))
    assert fit.t1 == pytest.approx(t1)
    assert fit.p == pytest.approx(p)
    assert fit.r2 == pytest.approx(1.0)
    assert fit.asymptote == pytest.approx(t1 / (1 - p))


def test_the_amdahl_fit_refuses_too_few_points_and_impossible_fractions() -> None:
    with pytest.raises(ValueError, match="three"):
        MATH.amdahl([1, 2], [1.0, 1.8])
    with pytest.raises(ValueError, match="positive"):
        MATH.amdahl([1, 2, 0], [1.0, 1.8, 2.0])
    # Rates that fall as cores are added fit a negative parallel fraction: refused.
    with pytest.raises(ValueError, match="outside"):
        MATH.amdahl([1, 2, 4], [4.0, 3.0, 2.0])


def test_the_marginal_gain_is_the_derivative_of_the_rate() -> None:
    fit = AmdahlFit(t1=0.8, p=0.92, r2=1.0, residuals=())
    for n in (1.0, 2.5, 7.0, 16.0):
        h = 1e-6
        numeric = (fit.rate(n + h) - fit.rate(n - h)) / (2 * h)
        assert fit.marginal(n) == pytest.approx(numeric, rel=1e-6)


def test_the_knee_solves_dT_dn_equal_to_the_threshold() -> None:
    fit = AmdahlFit(t1=0.8, p=0.92, r2=1.0, residuals=())
    theta = 0.05
    knee = MATH.knee(fit, theta)
    assert knee == pytest.approx((math.sqrt(0.8 * 0.92 / theta) - 0.92) / (1 - 0.92))
    assert fit.marginal(knee) == pytest.approx(theta)
    assert fit.marginal(knee - 0.5) > theta > fit.marginal(knee + 0.5)


def test_the_knee_at_the_edges_of_the_parallel_fraction() -> None:
    assert MATH.knee(AmdahlFit(1.0, 0.0, 1.0, ()), 0.1) == 1.0
    assert MATH.knee(AmdahlFit(1.0, 1.0, 1.0, ()), 0.1) == math.inf
    # A threshold above the first core's own gain: the knee is the first core.
    assert MATH.knee(AmdahlFit(1.0, 0.5, 1.0, ()), 100.0) == 1.0
    with pytest.raises(ValueError, match="positive"):
        MATH.knee(AmdahlFit(1.0, 0.5, 1.0, ()), 0)


def test_the_fewest_cores_for_a_floor_is_exact_and_says_when_none_suffice() -> None:
    fit = AmdahlFit(t1=1.0, p=0.9, r2=1.0, residuals=())  # asymptote 10 tok/s
    assert MATH.cores_for_rate(fit, 0.5) == 1
    need = MATH.cores_for_rate(fit, 4.0)
    assert need is not None
    assert fit.rate(need) >= 4.0 > fit.rate(need - 1)
    assert need == math.ceil(0.9 / (1.0 / 4.0 - 0.1))
    assert MATH.cores_for_rate(fit, 10.0) is None  # the asymptote itself is never reached
    assert MATH.cores_for_rate(fit, 25.0) is None


def test_the_ledger_integral_matches_a_numeric_integration() -> None:
    b, r0, r1, horizon = 120_000.0, 50.0, 0.2, 365.0
    closed = MATH.integral_of_linear_rate(b, r0, r1, horizon)
    steps = 100_000
    dt = horizon / steps
    numeric = sum(b * (r0 + r1 * (i + 0.5) * dt) * dt for i in range(steps))
    assert closed == pytest.approx(numeric, rel=1e-9)
    assert MATH.integral_of_linear_rate(b, r0, 0, horizon) == b * r0 * horizon
    with pytest.raises(ValueError, match="negative"):
        MATH.integral_of_linear_rate(b, r0, r1, -1)
