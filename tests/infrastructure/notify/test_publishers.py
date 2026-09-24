# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two notification transports, including the paths that fire without an
injected seam -- those are the ones that run in production."""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any
from uuid import UUID

import pytest

from vibey.infrastructure.notify.desktop import DesktopNotifier
from vibey.infrastructure.notify.events import NotificationEvent, NotificationKind
from vibey.infrastructure.notify.webhook import WebhookPublisher

PROJECT_ID = UUID("11111111-2222-3333-4444-555555555555")


def _event() -> NotificationEvent:
    return NotificationEvent(
        kind=NotificationKind.HUMAN_GATE_RAISED,
        project_id=PROJECT_ID,
        title="Gate raised",
        message='needs a "decision"',
    )


def _allow_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook.socket.getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )


# --- webhook -----------------------------------------------------------------


def test_the_signature_is_hmac_sha256_over_the_exact_bytes_sent() -> None:
    """A receiver recomputes over the body it got, so the signed bytes and the
    posted bytes have to be the same object, not the same dict re-serialised."""
    sent: dict[str, Any] = {}

    def capture(url: str, body: bytes, headers: dict[str, str]) -> bool:
        sent.update(url=url, body=body, headers=headers)
        return True

    publisher = WebhookPublisher(http_post_fn=capture)
    asyncio.run(publisher.publish(_event(), "https://example.test/hook", secret="s3cret"))

    expected = publisher.compute_signature(sent["body"], "s3cret")
    assert sent["headers"]["X-Vibey-Signature"] == expected
    assert expected.startswith("sha256=")
    assert json.loads(sent["body"])["title"] == "Gate raised"


def test_no_secret_means_no_signature_header_rather_than_an_empty_one() -> None:
    """An empty signature header reads as "signed, and it did not match"."""
    sent: dict[str, Any] = {}
    publisher = WebhookPublisher(http_post_fn=lambda u, b, h: bool(sent.update(headers=h)) or True)
    asyncio.run(publisher.publish(_event(), "https://example.test/hook"))
    assert "X-Vibey-Signature" not in sent["headers"]


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.test/x", "", "javascript:alert(1)"]
)
def test_the_real_poster_refuses_non_http_schemes(url: str) -> None:
    """The URL comes from project config, so the scheme check is what stops a
    notification from reading a local file or hitting an unexpected protocol."""
    publisher = WebhookPublisher()
    assert publisher._sync_post(url, b"{}", {}, 1.0) is False


def test_a_redirect_status_is_not_counted_as_delivered(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """http.client does not follow redirects by default — a 3xx response is not
    in the accepted 2xx set, so a redirect is simply not delivered."""

    class FakeResponse:
        status = 301

        def read(self, *args):  # type: ignore[no-untyped-def]
            return b""

    class FakeConnection:
        def __init__(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            self._response = FakeResponse()

        def request(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            return None

        def getresponse(self) -> FakeResponse:
            return self._response

        def close(self) -> None:
            return None

    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook._pinned_connection_class",
        lambda base, ip: lambda *a, **kw: FakeConnection(),
    )
    from vibey.infrastructure.notify.webhook import WebhookPublisher

    publisher = WebhookPublisher()
    assert publisher._sync_post("https://example.test/hook", b"{}", {}, 1.0) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://user:pass@example.test/hook",
        "http://example.test:bad/hook",
        "http://localhost/hook",
        "http://service.internal/hook",
    ],
)
def test_the_real_poster_refuses_unsafe_url_shapes(url: str) -> None:
    publisher = WebhookPublisher()
    assert publisher._sync_post(url, b"{}", {}, 1.0) is False


def test_the_real_poster_refuses_dns_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook.socket.getaddrinfo",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("DNS unavailable")),
    )
    assert WebhookPublisher()._sync_post("https://example.test/hook", b"{}", {}, 1.0) is False


def test_the_real_poster_refuses_empty_dns_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook.socket.getaddrinfo", lambda *args, **kwargs: []
    )
    assert WebhookPublisher()._sync_post("https://example.test/hook", b"{}", {}, 1.0) is False


def test_the_real_poster_refuses_malformed_dns_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook.socket.getaddrinfo",
        lambda *args, **kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ())],
    )
    assert WebhookPublisher()._sync_post("https://example.test/hook", b"{}", {}, 1.0) is False


def test_the_real_poster_reports_failure_rather_than_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A notification that cannot be delivered must not take the run with it."""

    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook._pinned_connection_class",
        lambda base, ip: lambda *a, **kw: (_ for _ in ()).throw(OSError("network is down")),
    )
    publisher = WebhookPublisher()
    assert publisher._sync_post("https://example.test/hook", b"{}", {}, 1.0) is False


@pytest.mark.parametrize(
    ("status", "delivered"), [(200, True), (204, True), (301, False), (500, False)]
)
def test_only_success_statuses_count_as_delivered(
    monkeypatch: pytest.MonkeyPatch, status: int, delivered: bool
) -> None:
    class _Response:
        def __init__(self) -> None:
            self.status = status

        def read(self) -> bytes:
            return b""

    class _Connection:
        _response_cls = _Response

        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        def request(self, *args: object, **kwargs: object) -> None:
            return None

        def getresponse(self) -> _Response:
            return self._response_cls()  # type: ignore[attr-defined]

        def close(self) -> None:
            return None

    _allow_public_dns(monkeypatch)
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook._pinned_connection_class",
        lambda base, ip: _Connection,
    )
    publisher = WebhookPublisher()
    assert publisher._sync_post("https://example.test/hook", b"{}", {}, 1.0) is delivered


def test_dns_rebinding_cannot_reconnect_to_a_different_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The IP validated during ``_resolve_safe_target`` is the same IP handed to
    ``socket.create_connection``.  A DNS record that resolves differently a second
    time cannot steer the connection to a private address, because the connection
    target is the IP from the first resolution, not the hostname."""
    import socket as _socket

    calls: list[tuple[str, int]] = []

    def spy_create_connection(addr, timeout=None, socket_options=None, source_address=None):
        calls.append(addr)
        raise OSError("connection refused")

    monkeypatch.setattr(_socket, "create_connection", spy_create_connection)
    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook.socket.getaddrinfo",
        lambda *a, **kw: [(_socket.AF_INET, _socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )

    publisher = WebhookPublisher()
    result = publisher._sync_post("http://example.test/hook", b"{}", {}, 1.0)

    assert result is False
    assert calls == [("93.184.216.34", 80)], f"connection went to {calls}, not the validated IP"


def test_a_url_with_query_string_is_delivered_to_the_pinned_ip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A webhook URL that already carries a query string preserves it — the
    path reconstruction in _sync_post must not drop it."""
    _allow_public_dns(monkeypatch)

    recorded: list[str] = []

    class FakeResponse:
        status = 200

        def read(self) -> bytes:
            return b""

    class FakeConnection:
        def __init__(self, host: str, port: int, timeout: float = 10.0) -> None:
            pass

        def request(self, method: str, path: str, *args: object, **kwargs: object) -> None:
            recorded.append(path)

        def getresponse(self) -> FakeResponse:
            return FakeResponse()

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        "vibey.infrastructure.notify.webhook._pinned_connection_class",
        lambda base, ip: FakeConnection,
    )
    publisher = WebhookPublisher()
    result = publisher._sync_post("https://example.test/hook?token=secret", b"{}", {}, 1.0)
    assert result is True
    assert recorded == ["/hook?token=secret"]


@pytest.mark.parametrize("url", ["http://127.0.0.1/hook", "http://169.254.169.254/latest"])
def test_the_real_poster_refuses_private_destinations(url: str) -> None:
    publisher = WebhookPublisher()
    assert publisher._sync_post(url, b"{}", {}, 1.0) is False


def test_publish_without_an_injected_poster_uses_the_real_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        WebhookPublisher, "_sync_post", lambda self, u, b, h, t: calls.append(u) or True
    )
    assert asyncio.run(WebhookPublisher().publish(_event(), "https://example.test/hook"))
    assert calls == ["https://example.test/hook"]


# --- desktop -----------------------------------------------------------------


def test_macos_and_linux_get_their_own_command() -> None:
    mac = DesktopNotifier(platform_override="darwin")._build_command(_event())
    assert mac[0] == "osascript"
    linux = DesktopNotifier(platform_override="linux")._build_command(_event())
    assert linux[0] == "notify-send"


def test_quotes_in_the_message_reach_applescript_as_data_not_source() -> None:
    """The message used to be interpolated into an AppleScript string literal with only
    its quotes escaped; it is an argument of a fixed script now, passed verbatim
    (test_desktop_injection.py has the attack)."""
    event = _event()
    cmd = DesktopNotifier(platform_override="darwin")._build_command(event)
    assert '"decision"' in event.message
    assert cmd[cmd.index("--") + 2] == event.message
    assert not any(event.message in part for part in cmd[: cmd.index("--")])


def test_an_unsupported_platform_is_a_no_op_not_a_crash() -> None:
    notifier = DesktopNotifier(platform_override="win32")
    assert notifier._build_command(_event()) == []
    assert asyncio.run(notifier.notify(_event())) is False


def test_an_injected_executor_is_used_instead_of_spawning() -> None:
    seen: list[list[str]] = []
    notifier = DesktopNotifier(
        executor=lambda cmd: bool(seen.append(cmd)) or True, platform_override="linux"
    )
    assert asyncio.run(notifier.notify(_event())) is True
    assert seen and seen[0][0] == "notify-send"


def test_desktop_notifier_real_subprocess_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Covers lines 35-36: the real subprocess path when no executor is injected."""

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_create(*args: object, **kwargs: object) -> FakeProcess:
        return FakeProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create)
    notifier = DesktopNotifier(platform_override="linux")
    assert asyncio.run(notifier.notify(_event())) is True


def test_a_failing_notifier_binary_does_not_take_the_run_with_it() -> None:
    notifier = DesktopNotifier(platform_override="linux")
    # notify-send is absent on macOS CI, and absent binaries raise on spawn.
    assert asyncio.run(notifier.notify(_event())) in {True, False}
