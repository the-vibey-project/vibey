# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one graded estimator (#88, #134): its fit, its refusals, its grades -- and proof
that lifting it out of the fit calculus changed nothing the fit calculus reports."""

from __future__ import annotations

import random

import pytest

from vibey_gh.estimation import (
    BASIS_LINEAR,
    BASIS_MEAN,
    BASIS_NONE,
    Grade,
    GradedEstimator,
    Prediction,
    Sample,
)
from vibey_gh.fit import Estimate, Observation, estimate_from
from vibey_gh.interfaces.graded_estimator_interface import GradedEstimatorInterface


def _legacy_estimate_from(observations: list[Observation], floor_slots: float = 1.0) -> Estimate:
    """`vibey_gh.fit.estimate_from` exactly as it stood before the estimator was lifted out
    (e1daff34), copied verbatim. The equivalence tests below hold the new wrapper to it."""
    if not observations:
        return Estimate(slots=floor_slots, base_s=0.0, rate_s_per_kb=0.0, samples=0)

    xs = [o.payload_bytes / 1024 for o in observations]
    ys = [o.elapsed_s for o in observations]
    n = len(observations)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    if var_x > 0:
        rate = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / var_x
        base = mean_y - rate * mean_x
    else:
        rate, base = 0.0, mean_y
    # Negative fits are physically meaningless; fall back to the flat mean.
    if base < 0 or rate < 0:
        rate, base = 0.0, mean_y

    concurrent = max((o.concurrent for o in observations), default=1)
    slots = max(float(min(concurrent, n)), floor_slots)
    return Estimate(
        slots=round(slots, 2),
        base_s=round(base, 1),
        rate_s_per_kb=round(rate, 3),
        samples=n,
    )


def _random_observations(rng: random.Random) -> list[Observation]:
    """A mix of every shape the fit meets: one size or many, rising or falling times,
    duplicates, zero payloads, and the odd negative reading from a broken clock."""
    n = rng.randint(0, 12)
    sizes = [rng.choice((0, 1024, 4096, 8192)) for _ in range(n)]
    if rng.random() < 0.6:
        sizes = [rng.randint(0, 200_000) for _ in range(n)]
    slope = rng.uniform(-0.01, 0.02)
    return [
        Observation(
            payload_bytes=size,
            elapsed_s=round(rng.uniform(-5.0, 300.0) + slope * size, rng.randint(0, 6)),
            concurrent=rng.randint(0, 16),
        )
        for size in sizes
    ]


# -- the wrapper is the old function -----------------------------------------------------


@pytest.mark.parametrize("seed", range(400))
def test_estimate_from_is_bit_identical_to_the_function_it_replaced(seed):
    """Every constant `vibey-gh fit` has ever printed comes from `estimate_from`. Moving its
    arithmetic into the shared estimator must not move a single one of them."""
    rng = random.Random(seed)
    observations = _random_observations(rng)
    floor = rng.choice((1.0, 0.5, 2.0, 1.234, 3.0))
    assert estimate_from(observations, floor) == _legacy_estimate_from(observations, floor)


@pytest.mark.parametrize(
    "observations",
    [
        [],
        [Observation(8192, 100.0, 2)],
        [Observation(8192, 100.0, 2), Observation(8192, 120.0, 2)],
        [Observation(1024, 60.0, 6), Observation(11264, 160.0, 6)],
        [Observation(1024, 200.0, 2), Observation(20480, 100.0, 2)],
        [Observation(1024, -10.0, 1), Observation(1024, -30.0, 1)],
        [Observation(0, 0.0, 0)],
    ],
)
def test_the_fit_calculus_edge_cases_are_unchanged(observations):
    assert estimate_from(observations) == _legacy_estimate_from(observations)
    assert estimate_from(observations, 1.234) == _legacy_estimate_from(observations, 1.234)


def test_an_observation_reads_as_kilobytes_against_seconds():
    assert Observation(payload_bytes=2048, elapsed_s=12.5, concurrent=3).sample == Sample(2.0, 12.5)


def test_the_fit_calculus_takes_whichever_estimator_it_is_handed():
    class Fixed:
        def fit(self, samples):
            from vibey_gh.estimation import LinearFit

            return LinearFit(intercept=7.04, slope=0.1234, n=len(samples), basis="x", reason="y")

    est = estimate_from([Observation(1024, 1.0, 1)], estimator=Fixed())
    assert est == Estimate(slots=1.0, base_s=7.0, rate_s_per_kb=0.123, samples=1)


# -- the estimator on its own ------------------------------------------------------------


def test_the_estimator_declares_its_seam():
    assert isinstance(GradedEstimator(), GradedEstimatorInterface)


def test_no_samples_predicts_nothing_rather_than_zero():
    line = GradedEstimator().fit([])
    assert (line.n, line.basis, line.intercept, line.slope) == (0, BASIS_NONE, 0.0, 0.0)
    prediction = GradedEstimator().predict([], x=8.0)
    assert prediction.value is None and not prediction.known
    assert prediction.basis == BASIS_NONE and prediction.n == 0
    assert "nothing has been measured" in prediction.reason


def test_one_distinct_x_puts_everything_in_the_intercept():
    line = GradedEstimator().fit([Sample(8.0, 100.0), Sample(8.0, 120.0)])
    assert line.basis == BASIS_MEAN and line.slope == 0.0 and line.intercept == 110.0
    assert "cannot be separated" in line.reason


def test_distinct_x_recovers_the_line():
    line = GradedEstimator().fit([Sample(1.0, 60.0), Sample(11.0, 160.0)])
    assert line.basis == BASIS_LINEAR
    assert line.slope == pytest.approx(10.0) and line.intercept == pytest.approx(50.0)
    assert line.at(3.0) == pytest.approx(80.0)
    prediction = GradedEstimator().predict([Sample(1.0, 60.0), Sample(11.0, 160.0)], x=3.0)
    assert prediction == Prediction(
        value=pytest.approx(80.0), x=3.0, basis=BASIS_LINEAR, n=2, reason=line.reason
    )
    assert prediction.known


def test_a_negative_term_falls_back_to_the_flat_mean():
    samples = [Sample(1.0, 200.0), Sample(20.0, 100.0)]
    line = GradedEstimator().fit(samples)
    assert line.basis == BASIS_MEAN and line.slope == 0.0 and line.intercept == 150.0
    assert "physically meaningless" in line.reason


def test_a_quantity_that_may_go_negative_keeps_its_slope():
    line = GradedEstimator(nonnegative=False).fit([Sample(1.0, 200.0), Sample(20.0, 100.0)])
    assert line.basis == BASIS_LINEAR and line.slope < 0


# -- grading -----------------------------------------------------------------------------


def test_a_grade_sets_the_prediction_beside_the_actual():
    estimator = GradedEstimator()
    prediction = estimator.predict([Sample(0.0, 100.0)])
    grade = estimator.grade(prediction, actual=125.0)
    assert grade == Grade(predicted=100.0, actual=125.0, basis=BASIS_MEAN, n=1)
    # Positive error is under-prediction: the direction that misses deadlines.
    assert grade.error == 25.0 and grade.abs_error == 25.0 and grade.relative_error == 0.2


def test_a_prediction_without_a_value_is_ungraded_not_wrong():
    grade = GradedEstimator().grade(GradedEstimator().predict([]), actual=40.0)
    assert grade.predicted is None
    assert grade.error is None and grade.abs_error is None and grade.relative_error is None


def test_an_actual_of_zero_has_no_relative_error():
    grade = Grade(predicted=3.0, actual=0.0, basis=BASIS_MEAN, n=1)
    assert grade.error == -3.0 and grade.relative_error is None


def test_the_track_record_is_kept_over_what_could_be_judged():
    estimator = GradedEstimator()
    grades = [
        Grade(predicted=100.0, actual=110.0, basis=BASIS_MEAN, n=3),
        Grade(predicted=100.0, actual=80.0, basis=BASIS_MEAN, n=3),
        Grade(predicted=None, actual=50.0, basis=BASIS_NONE, n=0),
    ]
    record = estimator.track_record(grades)
    assert (record.graded, record.ungraded) == (2, 1)
    assert record.mean_error == -5.0 and record.mean_abs_error == 15.0


def test_a_record_with_nothing_to_judge_says_so():
    record = GradedEstimator().track_record([Grade(None, 1.0, BASIS_NONE, 0)])
    assert (record.graded, record.ungraded) == (0, 1)
    assert record.mean_error is None and record.mean_abs_error is None
    assert GradedEstimator().track_record([]).graded == 0
