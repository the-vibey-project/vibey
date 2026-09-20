# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The stdlib-backed default behind the `Logger` seam."""

import logging

import pytest

from vibey.application.interfaces import Logger
from vibey.application.observability import StandardLibraryLogger


def test_it_satisfies_the_logger_seam() -> None:
    assert isinstance(StandardLibraryLogger("vibey.test"), Logger)


def test_an_event_with_no_fields_renders_as_just_the_event(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log = StandardLibraryLogger("vibey.test.bare")

    with caplog.at_level(logging.INFO, logger="vibey.test.bare"):
        log.info("job.deferred")

    assert caplog.records[0].getMessage() == "job.deferred"


def test_bound_context_and_call_fields_are_both_rendered(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log = StandardLibraryLogger("vibey.test.fields", owner="w1")

    with caplog.at_level(logging.INFO, logger="vibey.test.fields"):
        log.info("job.deferred", kind="build.implement")

    assert caplog.records[0].getMessage() == "job.deferred owner=w1 kind=build.implement"


def test_bind_returns_a_new_logger_and_leaves_the_original_alone(
    caplog: pytest.LogCaptureFixture,
) -> None:
    log = StandardLibraryLogger("vibey.test.bind", owner="w1")

    bound = log.bind(job_id="j-1")

    assert bound is not log
    with caplog.at_level(logging.INFO, logger="vibey.test.bind"):
        bound.info("job.deferred")
        log.info("job.deferred")

    assert caplog.records[0].getMessage() == "job.deferred owner=w1 job_id=j-1"
    assert caplog.records[1].getMessage() == "job.deferred owner=w1"


@pytest.mark.parametrize(
    ("method", "level"),
    [
        ("debug", logging.DEBUG),
        ("info", logging.INFO),
        ("warning", logging.WARNING),
        ("error", logging.ERROR),
    ],
)
def test_every_level_reaches_the_stdlib_hierarchy_at_that_level(
    caplog: pytest.LogCaptureFixture, method: str, level: int
) -> None:
    log = StandardLibraryLogger("vibey.test.levels")

    with caplog.at_level(logging.DEBUG, logger="vibey.test.levels"):
        getattr(log, method)("an.event", detail="d")

    assert caplog.records[0].levelno == level
    assert caplog.records[0].getMessage() == "an.event detail=d"
