# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The operator's declaration of how long conformance waits for a run directory."""

import pytest

from vibey.infrastructure.engines.conformance_window import (
    CONFORMANCE_POLL_ENV,
    conformance_poll_seconds,
)


@pytest.mark.parametrize("environ", [{}, {CONFORMANCE_POLL_ENV: ""}, {CONFORMANCE_POLL_ENV: "  "}])
def test_unset_or_blank_leaves_the_built_in_default(environ: dict[str, str]) -> None:
    assert conformance_poll_seconds(environ) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("420", 420.0), (" 90.5 ", 90.5), ("0.25", 0.25), ("1e3", 1000.0)],
)
def test_a_positive_finite_number_is_taken_as_written(raw: str, expected: float) -> None:
    assert conformance_poll_seconds({CONFORMANCE_POLL_ENV: raw}) == expected


def test_text_is_refused_naming_the_variable() -> None:
    with pytest.raises(ValueError, match=CONFORMANCE_POLL_ENV) as raised:
        conformance_poll_seconds({CONFORMANCE_POLL_ENV: "soon"})
    assert "number of seconds" in str(raised.value)


@pytest.mark.parametrize("raw", ["0", "-30", "-0.5", "nan", "inf", "-inf"])
def test_zero_negative_and_non_finite_are_refused_not_defaulted(raw: str) -> None:
    with pytest.raises(ValueError, match=CONFORMANCE_POLL_ENV) as raised:
        conformance_poll_seconds({CONFORMANCE_POLL_ENV: raw})
    assert "above zero" in str(raised.value)
