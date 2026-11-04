# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for sovereign surface delivery in NotificationService (Issue #724)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from vibey.application.interfaces.messaging import MessagingPort
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.messaging.in_memory import InMemoryMessaging
from vibey.infrastructure.messaging.matrix import MatrixMessagingAdapter
from vibey.infrastructure.notify import DesktopNotifier, NotificationService
from vibey.infrastructure.notify.interfaces import NotificationServiceInterface
from vibey.infrastructure.sms.in_memory import InMemorySms

try:
    from tests.fakes.http import InMemoryHttpServer
except ModuleNotFoundError:
    import http
    import io
    import json
    import sys
    import types
    import urllib.error
    import urllib.request
    from collections.abc import Mapping
    from dataclasses import dataclass
    from typing import Any

    @dataclass(frozen=True)
    class RecordedRequest:
        method: str
        url: str
        headers: dict[str, str]
        body: bytes | None
        timeout: float | None

    class InMemoryHttpResponse:
        def __init__(
            self, body: bytes, status: int = 200, headers: Mapping[str, str] | None = None
        ) -> None:
            self._body = body
            self.status = status
            self.headers = dict(headers or {})

        def __enter__(self) -> InMemoryHttpResponse:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def read(self) -> bytes:
            return self._body

    class InMemoryHttpServer:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.requests: list[RecordedRequest] = []
            self._prefix_routes: list[tuple[str, str, int, bytes, dict[str, str]]] = []

        def route_prefix(
            self,
            method: str,
            url_prefix: str,
            *,
            status: int = 200,
            body: bytes | str | Mapping[str, Any] = b"",
            headers: Mapping[str, str] | None = None,
        ) -> None:
            raw_body = (
                json.dumps(body).encode("utf-8")
                if isinstance(body, Mapping)
                else body.encode("utf-8")
                if isinstance(body, str)
                else body
            )
            self._prefix_routes.append(
                (method.upper(), url_prefix, status, raw_body, dict(headers or {}))
            )

        def __call__(
            self, request: urllib.request.Request, timeout: float | None = None
        ) -> InMemoryHttpResponse:
            method = request.get_method()
            url = request.full_url
            headers = {k.lower(): v for k, v in request.headers.items()}
            body = request.data if isinstance(request.data, bytes) else None
            rec = RecordedRequest(
                method=method, url=url, headers=headers, body=body, timeout=timeout
            )
            self.requests.append(rec)

            for m, prefix, status, resp_body, hdrs in self._prefix_routes:
                if m == method and url.startswith(prefix):
                    if status >= 400:
                        try:
                            reason = http.HTTPStatus(status).phrase
                        except ValueError:
                            reason = "Error"
                        raise urllib.error.HTTPError(
                            url, status, reason, dict(hdrs), io.BytesIO(resp_body)
                        )
                    return InMemoryHttpResponse(resp_body, status, hdrs)

            raise urllib.error.URLError(f"no route for {method} {url}")

    mod = types.ModuleType("tests.fakes.http")
    mod.InMemoryHttpServer = InMemoryHttpServer  # type: ignore[attr-defined]
    sys.modules["tests.fakes.http"] = mod


@pytest.mark.asyncio
async def test_an_enabled_project_notifies_the_matrix_room() -> None:
    messaging = InMemoryMessaging()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=messaging,
        messaging_room="!ops:matrix.test",
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="human_gate_raised",
        title="Human Gate Raised",
        message="answer the gate",
        config={"notifications": {"enabled": True, "desktop": False}},
    )
    assert result == {"desktop": False, "webhooks": [], "messaging": True}
    assert messaging.sent == [
        {"channel_id": "!ops:matrix.test", "message": "[vibey] Human Gate Raised\nanswer the gate"}
    ]


@pytest.mark.asyncio
async def test_each_email_and_sms_recipient_gets_the_notification() -> None:
    email = InMemoryEmail()
    sms = InMemorySms()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        email=email,
        sms=sms,
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": ["ops1@example.com", "ops2@example.com"],
                "sms_to": ["+15551234567"],
            }
        },
    )
    assert result == {"desktop": False, "webhooks": [], "email": [True, True], "sms": [True]}
    assert len(email.sent) == 2
    assert email.sent[0] == {
        "to": "ops1@example.com",
        "subject": "[vibey] Run Completed",
        "body": "done",
    }
    assert email.sent[1] == {
        "to": "ops2@example.com",
        "subject": "[vibey] Run Completed",
        "body": "done",
    }
    assert sms.sent_sms == [
        {"phone_number": "+15551234567", "message": "[vibey] Run Completed: done"}
    ]


@pytest.mark.asyncio
async def test_messaging_can_be_switched_off_per_project() -> None:
    messaging = InMemoryMessaging()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=messaging,
        messaging_room="!ops:matrix.test",
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="human_gate_raised",
        title="Human Gate Raised",
        message="answer the gate",
        config={"notifications": {"enabled": True, "desktop": False, "messaging": False}},
    )
    assert result == {"enabled": False, "desktop": False, "webhooks": []}
    assert messaging.sent == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("room", "port"),
    [
        (None, InMemoryMessaging()),
        ("  ", InMemoryMessaging()),
        ("", InMemoryMessaging()),
        ("!ops:matrix.test", None),
    ],
)
async def test_no_room_or_no_port_means_no_matrix_delivery(
    room: str | None, port: MessagingPort | None
) -> None:
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=port,
        messaging_room=room,
    )
    proj_service = service.for_project_config(
        {"notifications": {"enabled": True, "desktop": False}}
    )
    assert not proj_service.has_channels()
    result = await service.notify(
        project_id=uuid4(),
        kind="human_gate_raised",
        title="Human Gate Raised",
        message="answer the gate",
        config={"notifications": {"enabled": True, "desktop": False}},
    )
    assert result == {"enabled": False, "desktop": False, "webhooks": []}
    if port is not None:
        assert isinstance(port, InMemoryMessaging)
        assert port.sent == []


@pytest.mark.asyncio
async def test_recipients_without_their_port_are_not_delivered() -> None:
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        email=None,
        sms=None,
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": ["ops@example.com"],
                "sms_to": ["+15551234567"],
            }
        },
    )
    assert result == {"enabled": False, "desktop": False, "webhooks": []}


@pytest.mark.asyncio
async def test_a_failing_sovereign_sink_is_reported_not_raised() -> None:
    server = InMemoryHttpServer()
    server.route_prefix("PUT", "https://matrix.test/", status=502)
    matrix = MatrixMessagingAdapter(url="https://matrix.test", token="t", opener=server)
    email = InMemoryEmail()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=matrix,
        messaging_room="!ops:matrix.test",
        email=email,
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": ["ops@example.com"],
            }
        },
    )
    assert result == {
        "desktop": False,
        "webhooks": [],
        "messaging": False,
        "email": [True],
    }
    assert len(email.sent) == 1


@pytest.mark.asyncio
async def test_malformed_recipient_lists_are_ignored() -> None:
    email = InMemoryEmail()
    sms = InMemorySms()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        email=email,
        sms=sms,
    )
    # Case 1: string / non-sequence
    res1 = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": "ops@example.com",
                "sms_to": "+15551234567",
            }
        },
    )
    assert res1 == {"enabled": False, "desktop": False, "webhooks": []}
    assert email.sent == []
    assert sms.sent_sms == []

    # Case 2: [None, " ", 7]
    res2 = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": [None, " ", 7],
                "sms_to": [None, " ", 7],
            }
        },
    )
    assert res2 == {"enabled": False, "desktop": False, "webhooks": []}
    assert email.sent == []
    assert sms.sent_sms == []


@pytest.mark.asyncio
async def test_a_disabled_project_uses_no_channel() -> None:
    messaging = InMemoryMessaging()
    email = InMemoryEmail()
    sms = InMemorySms()
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=messaging,
        messaging_room="!ops:matrix.test",
        email=email,
        sms=sms,
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": False,
                "desktop": True,
                "messaging": True,
                "email_to": ["ops@example.com"],
                "sms_to": ["+15551234567"],
            }
        },
    )
    assert result == {"enabled": False, "desktop": False, "webhooks": []}
    assert messaging.sent == []
    assert email.sent == []
    assert sms.sent_sms == []


@pytest.mark.asyncio
async def test_results_never_carry_a_recipient() -> None:
    room = "!secret-room:matrix.test"
    addr = "secret-person@example.com"
    number = "+15559876543"
    service = NotificationService(
        desktop_notifier=DesktopNotifier(executor=lambda cmd: True, platform_override="linux"),
        messaging=InMemoryMessaging(),
        messaging_room=room,
        email=InMemoryEmail(),
        sms=InMemorySms(),
    )
    result = await service.notify(
        project_id=uuid4(),
        kind="run_completed",
        title="Run Completed",
        message="done",
        config={
            "notifications": {
                "enabled": True,
                "desktop": False,
                "email_to": [addr],
                "sms_to": [number],
            }
        },
    )
    res_str = repr(result)
    assert room not in res_str
    assert addr not in res_str
    assert number not in res_str


def test_the_service_satisfies_its_interface() -> None:
    service = NotificationService()
    assert isinstance(service, NotificationServiceInterface)


def test_has_channels_with_only_sms() -> None:
    sms = InMemorySms()
    service = NotificationService(
        enable_desktop=False,
        sms=sms,
        sms_to=["+15551234567"],
    )
    assert service.has_channels() is True


def test_recipients_helper_tolerance() -> None:
    assert NotificationService._recipients(123) == ()
    assert NotificationService._recipients(None) == ()
    assert NotificationService._recipients("alice@example.com") == ()
    assert NotificationService._recipients(b"alice@example.com") == ()
    assert NotificationService._recipients(["  bob@example.com  ", "  ", None, 42]) == (
        "bob@example.com",
    )
