# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One search request under a total deadline: headers and body together, however slowly a
listener sends them."""

from __future__ import annotations

import threading
import time
import urllib.request

import pytest

from tests.infrastructure.web.searxng_fakes import FakeResponse
from vibey.infrastructure.web.bounded_request import Answered, BoundedRequest, DeadlineExceeded
from vibey.infrastructure.web.interfaces import BoundedRequestInterface

REQUEST = urllib.request.Request("http://127.0.0.1:28180/config")  # noqa: S310 - never opened


def test_the_class_honours_its_interface() -> None:
    assert isinstance(BoundedRequest(lambda request, timeout: None), BoundedRequestInterface)


def test_an_answer_in_time_is_its_body_and_where_it_came_from() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        assert timeout == 3
        return FakeResponse(b"body", url="http://127.0.0.1:28180/config2")

    answered = BoundedRequest(opener).fetch(REQUEST, deadline=3, limit=10)
    assert answered == Answered(b"body", "http://127.0.0.1:28180/config2")


def test_a_response_that_does_not_say_where_it_came_from_is_taken_as_asked() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        return FakeResponse(b"x")

    assert BoundedRequest(opener).fetch(REQUEST, deadline=3, limit=10).url == REQUEST.full_url


def test_the_openers_own_error_is_raised_as_it_was() -> None:
    def opener(request: urllib.request.Request, timeout: float) -> FakeResponse:
        raise ConnectionRefusedError("refused")

    with pytest.raises(ConnectionRefusedError, match="refused"):
        BoundedRequest(opener).fetch(REQUEST, deadline=3, limit=10)


def test_a_request_still_going_at_the_deadline_is_abandoned_on_time() -> None:
    release = threading.Event()

    def stuck(request: urllib.request.Request, timeout: float) -> FakeResponse:
        release.wait(10)
        return FakeResponse(b"late")

    started = time.monotonic()
    try:
        with pytest.raises(DeadlineExceeded, match="no complete answer within 0.2s"):
            BoundedRequest(stuck).fetch(REQUEST, deadline=0.2, limit=10)
        assert time.monotonic() - started < 2
    finally:
        release.set()
