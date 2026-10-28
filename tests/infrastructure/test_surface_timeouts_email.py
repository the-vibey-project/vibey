# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SMTP email adapter bounds every connection with a timeout (#730).

A relay that accepts the connection and never answers must not block the caller for ever. The
tests use a real listening socket on loopback that never speaks, so the bound is what ends the
call -- no import is patched and no outside service is reached. The implicit-TLS branch (port
465, which an unprivileged process cannot listen on) is covered by
`test_forward_email_adapter_uses_implicit_tls_on_port_465` in `test_sovereign_surfaces.py`, which
asserts `SMTP_SSL` is opened with the timeout.
"""

from __future__ import annotations

import asyncio
import inspect
import socket
import time
from collections.abc import Iterator
from contextlib import closing, contextmanager

import pytest

from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.email.forward_email import ForwardEmailAdapter


@contextmanager
def _silent_server() -> Iterator[int]:
    """A listening socket whose backlog completes handshakes but which never reads or writes."""
    with closing(socket.socket()) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        yield int(server.getsockname()[1])


@pytest.mark.parametrize("password", [None, "pw"])
def test_a_silent_relay_ends_a_submission_at_the_timeout(password: str | None) -> None:
    with _silent_server() as port:
        adapter = ForwardEmailAdapter(
            smtp_host="127.0.0.1", smtp_port=port, username="u", password=password, timeout=0.3
        )
        started = time.monotonic()
        with pytest.raises(OSError):  # TimeoutError is an OSError
            asyncio.run(adapter.send_email("ops@example.org", "s", "b"))
    assert time.monotonic() - started < 5


def test_the_adapter_defaults_to_the_surface_timeout() -> None:
    parameter = inspect.signature(ForwardEmailAdapter.__init__).parameters["timeout"]
    assert parameter.default == DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
