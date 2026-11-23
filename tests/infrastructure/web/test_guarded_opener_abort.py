# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A request abandoned at its deadline does not keep its thread (SP-ACP Task 9c, P-9c-3).

`GuardedOpener` records the socket each of its connections connects, under the thread that
opened it (the `threading.Thread` itself, never its reusable ident); `abort(thread)` shuts those
sockets down, so a read blocked in that thread wakes and ends -- in the status line, the headers
or the body -- instead of living as long as a trickling listener likes. The real path is tested
against a loopback listener this test controls: it answers the headers (or nothing), then holds
until the test lets it go.
"""

from __future__ import annotations

import contextlib
import http.client
import socket
import threading
import urllib.request
from collections.abc import Iterator
from typing import Any

import pytest

from tests.infrastructure.web.searxng_fakes import FakeResponse
from vibey.infrastructure.web.bounded_request import BoundedRequest, DeadlineExceeded
from vibey.infrastructure.web.guarded_opener import GuardedOpener
from vibey.infrastructure.web.interfaces.guarded_opener_interface import (
    AbortableOpenerInterface,
)

REQUEST = urllib.request.Request("http://127.0.0.1:28180/config")  # noqa: S310 - never opened


class _Holding:
    """A loopback listener that answers a request's status line and headers at once (or
    nothing at all), then sends no more until `release` is set."""

    def __init__(self, *, headers: bool) -> None:
        self.release = threading.Event()
        self._headers = headers
        self._listener = socket.create_server(("127.0.0.1", 0))
        self.url = f"http://127.0.0.1:{self._listener.getsockname()[1]}/config"
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        with contextlib.suppress(OSError):
            client, _ = self._listener.accept()
            with client:
                client.recv(65536)
                if self._headers:
                    client.sendall(
                        b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n"
                        b"Content-Length: 1000\r\n\r\n{"
                    )
                self.release.wait(30)

    def close(self) -> None:
        self.release.set()
        self._listener.close()
        self._thread.join(5)


class _Recording(GuardedOpener):
    """The real opener, remembering the thread each request ran in. Each read's own socket
    timeout is made longer than the test, as a listener that sends one byte just inside it every
    time makes it in effect: only the total deadline, and its abort, can end the request."""

    def __init__(self, base_url: str) -> None:
        super().__init__(base_url)
        self.ran_in: list[threading.Thread] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.ran_in.append(threading.current_thread())
        return super().__call__(request, 60)


@pytest.fixture
def holding(request: pytest.FixtureRequest) -> Iterator[_Holding]:
    listener = _Holding(headers=request.param)
    try:
        yield listener
    finally:
        listener.close()


def test_the_opener_can_abort_what_a_thread_opened() -> None:
    assert isinstance(GuardedOpener("http://127.0.0.1:1"), AbortableOpenerInterface)


@pytest.mark.web_network  # the real opener, against this test's own loopback listener
@pytest.mark.parametrize("holding", [True, False], indirect=True, ids=["body", "headers"])
def test_a_request_held_past_its_deadline_ends_its_thread(holding: _Holding) -> None:
    """Review 1 M-1: urllib closes the connection's own handle once the headers are in, so the
    body is read from a socket the connection no longer names. The socket is recorded when it
    connects, and shut down from there, in either phase."""
    opener = _Recording(holding.url)
    with pytest.raises(DeadlineExceeded):
        BoundedRequest(opener).fetch(
            urllib.request.Request(holding.url),  # noqa: S310 - this test's loopback listener
            deadline=0.5,
            limit=4096,
        )
    (worker,) = opener.ran_in
    worker.join(5)  # bounded: the listener itself holds for 30 s
    assert not worker.is_alive()
    assert opener.threads() == frozenset()


class _Wire:
    """A connection's `connect` on a local socket pair: no network."""

    def __init__(self) -> None:
        self.ours, self.peer = socket.socketpair()

    def connect(self, connection: http.client.HTTPConnection) -> None:
        connection.sock = self.ours


class _SameIdent(threading.Thread):
    """A thread whose ident reads as every other's: an ident reused once a thread ends."""

    @property
    def ident(self) -> int:
        return 42


def test_abort_touches_only_the_given_threads_sockets_even_when_idents_repeat(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Review 1 I-1: thread idents are reused. A request whose thread ended, and a new one in a
    thread with the same ident: aborting the first never shuts the second's socket."""
    wires = {"first": _Wire(), "second": _Wire()}
    monkeypatch.setattr(
        http.client.HTTPConnection,
        "connect",
        lambda self: wires[threading.current_thread().name].connect(self),
    )
    opener = GuardedOpener("http://127.0.0.1:1")
    connected = threading.Event()

    def open_in(name: str, hold: threading.Event | None = None) -> threading.Thread:
        def run() -> None:
            connection = opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
            connection.connect()
            connected.set()
            if hold is not None:
                hold.wait(5)

        thread = _SameIdent(target=run, name=name)
        thread.start()
        return thread

    ended = open_in("first")
    ended.join(5)
    connected.clear()
    hold = threading.Event()
    live = open_in("second", hold)
    try:
        assert connected.wait(5) and ended.ident == live.ident
        opener.abort(ended)  # long gone: nothing of the live request is touched
        peer = wires["second"].peer
        peer.settimeout(0)
        with pytest.raises(BlockingIOError):
            peer.recv(1)
        opener.abort(live)
        peer.settimeout(5)
        assert peer.recv(1) == b""  # shut down: its reader would wake now
    finally:
        hold.set()
        live.join(5)
    for wire in wires.values():
        wire.ours.close()
        wire.peer.close()


def test_a_connection_that_never_connected_has_nothing_to_shut_down() -> None:
    opener = GuardedOpener("http://127.0.0.1:1")
    made = opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
    opener.abort(threading.current_thread())
    assert made.sock is None and opener.threads() == frozenset()


class _Stuck:
    """An opener whose request never ends until it is aborted, as a trickling listener's."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.aborted: list[threading.Thread] = []
        self.ran_in: list[threading.Thread] = []

    def __call__(self, request: urllib.request.Request, timeout: float) -> Any:
        self.ran_in.append(threading.current_thread())
        self.release.wait(10)
        raise ConnectionResetError("shut down")

    def abort(self, thread: threading.Thread) -> None:
        self.aborted.append(thread)
        self.release.set()


def test_a_request_abandoned_at_its_deadline_is_aborted_by_its_own_thread() -> None:
    opener = _Stuck()
    with pytest.raises(DeadlineExceeded):
        BoundedRequest(opener).fetch(REQUEST, deadline=0.1, limit=10)
    assert opener.aborted == opener.ran_in  # the Thread object itself, never a reusable ident


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


def test_a_connect_that_left_no_socket_records_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(http.client.HTTPConnection, "connect", lambda self: None)
    opener = GuardedOpener("http://127.0.0.1:1")
    opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1).connect()
    assert opener.threads() == frozenset()


def _in_thread(work: Any) -> tuple[threading.Thread, list[BaseException]]:
    raised: list[BaseException] = []

    def run() -> None:
        try:
            work()
        except BaseException as exc:  # noqa: BLE001 - recorded for the test to read
            raised.append(exc)

    thread = threading.Thread(target=run)
    return thread, raised


def test_a_connect_that_completes_after_the_abort_is_shut_down_at_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Security review of the M-1 fix: a hop already connecting when the deadline aborts its
    thread finishes after the abort; its fresh socket is shut down at once and the request
    unwinds, never stored for nobody to shut down."""
    wire, go, entered = _Wire(), threading.Event(), threading.Event()

    def slow_connect(self: http.client.HTTPConnection) -> None:
        entered.set()
        go.wait(5)
        self.sock = wire.ours

    monkeypatch.setattr(http.client.HTTPConnection, "connect", slow_connect)
    opener = GuardedOpener("http://127.0.0.1:1")
    thread, raised = _in_thread(
        lambda: opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1).connect()
    )
    thread.start()
    assert entered.wait(5)
    opener.abort(thread)  # the deadline passes while the connect is still under way
    go.set()
    thread.join(5)
    assert [type(exc) for exc in raised] == [ConnectionAbortedError]
    wire.peer.settimeout(5)
    assert wire.peer.recv(1) == b""  # shut down, not left open
    assert opener.threads() == frozenset()
    wire.ours.close()
    wire.peer.close()


def test_no_hop_connects_once_its_thread_was_aborted(monkeypatch: pytest.MonkeyPatch) -> None:
    connects: list[str] = []
    monkeypatch.setattr(http.client.HTTPConnection, "connect", lambda self: connects.append("x"))
    opener = GuardedOpener("http://127.0.0.1:1")
    ready, go = threading.Event(), threading.Event()

    def later_hop() -> None:
        made = opener.connection(http.client.HTTPConnection)("127.0.0.1", timeout=1)
        ready.set()
        go.wait(5)
        made.connect()  # a redirect's next hop, after the deadline

    thread, raised = _in_thread(later_hop)
    thread.start()
    assert ready.wait(5)
    opener.abort(thread)
    go.set()
    thread.join(5)
    assert connects == [] and [type(exc) for exc in raised] == [ConnectionAbortedError]
