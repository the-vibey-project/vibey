# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A request abandoned at its deadline does not keep its thread (SP-ACP Task 9c, P-9c-3).

`GuardedOpener` keeps the connections each thread opened; `abort(thread)` shuts their sockets
down, so a reader blocked in that thread wakes and ends instead of living as long as a trickling
listener likes. No network: the connection's socket is one end of a local socket pair.
"""

from __future__ import annotations

import http.client
import socket
import threading
import urllib.error
import urllib.request
from typing import Any

import pytest

from tests.infrastructure.web.searxng_fakes import FakeResponse
from vibey.infrastructure.web.bounded_request import BoundedRequest, DeadlineExceeded
from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.interfaces.guarded_opener_interface import (
    AbortableOpenerInterface,
)

REQUEST = urllib.request.Request("http://127.0.0.1:28180/config")  # noqa: S310 - never opened


def test_the_opener_can_abort_what_a_thread_opened() -> None:
    assert isinstance(GuardedOpener("http://127.0.0.1:1"), AbortableOpenerInterface)


@pytest.mark.web_network  # the real opener; its connect is stood in for, so no socket leaves
@pytest.mark.parametrize(
    ("url", "kind"),
    [
        ("http://127.0.0.1:9/x", http.client.HTTPConnection),
        ("https://127.0.0.1:9/x", http.client.HTTPSConnection),
    ],
)
def test_abort_shuts_down_the_connections_this_thread_opened(
    monkeypatch: pytest.MonkeyPatch, url: str, kind: type[http.client.HTTPConnection]
) -> None:
    ours, peer = socket.socketpair()
    made: list[http.client.HTTPConnection] = []

    def connect(self: http.client.HTTPConnection) -> None:
        made.append(self)
        self.sock = ours  # as a connected socket would be, then the request fails
        raise OSError("no network here")

    monkeypatch.setattr(kind, "connect", connect)
    monkeypatch.setattr(kind, "close", lambda self: None)  # left connected, as a stuck read is
    opener = GuardedOpener(url)
    with pytest.raises(urllib.error.URLError):
        opener(urllib.request.Request(url), timeout=1)  # noqa: S310 - never reaches a network
    assert len(made) == 1 and made[0].sock is ours

    opener.abort(threading.get_ident() + 1)  # another thread's: nothing of this one is touched
    peer.settimeout(0)
    with pytest.raises(BlockingIOError):
        peer.recv(1)
    opener.abort(threading.get_ident())
    peer.settimeout(5)
    assert peer.recv(1) == b""  # shut down: a reader blocked on it would wake now
    opener.abort(threading.get_ident())  # once only: nothing is left to abort
    ours.close()
    peer.close()


def test_a_connection_with_no_socket_yet_is_skipped() -> None:
    opener = GuardedOpener("http://127.0.0.1:1")
    opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
    opener.abort(threading.get_ident())  # connecting had not begun: nothing to shut down


def test_a_finished_threads_connections_are_forgotten() -> None:
    opener = GuardedOpener("http://127.0.0.1:1")
    gone: list[int] = []

    def open_one() -> None:
        opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
        gone.append(threading.get_ident())

    worker = threading.Thread(target=open_one)
    worker.start()
    worker.join()
    opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
    assert opener.threads() == {threading.get_ident()}  # the finished thread's are gone


class _Stuck:
    """An opener whose request never ends until it is aborted, as a trickling listener's."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.aborted: list[int] = []
        self.ran_in: list[int] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.ran_in.append(threading.get_ident())
        self.release.wait(10)
        raise ConnectionResetError("shut down")

    def abort(self, thread_id: int) -> None:
        self.aborted.append(thread_id)
        self.release.set()


def test_a_request_abandoned_at_its_deadline_is_aborted_in_its_own_thread() -> None:
    opener = _Stuck()
    with pytest.raises(DeadlineExceeded):
        BoundedRequest(opener).fetch(REQUEST, deadline=0.1, limit=10)
    assert opener.aborted == opener.ran_in  # its own thread's connections, no other's


def test_an_opener_that_cannot_abort_is_left_to_end_on_its_own() -> None:
    release = threading.Event()

    def stuck(request: urllib.request.Request, timeout: float) -> FakeResponse:
        release.wait(10)
        return FakeResponse(b"late")

    try:
        with pytest.raises(DeadlineExceeded):
            BoundedRequest(stuck).fetch(REQUEST, deadline=0.1, limit=10)
    finally:
        release.set()
