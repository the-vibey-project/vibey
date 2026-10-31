# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A notification on a Linux host with no desktop session is `False`, never an exception (#1116).

A headless server has no `notify-send`, or has it but no D-Bus session to talk to. The
notifier is best effort: nothing it can run into may stop a worker, so each way a headless
host fails answers `False` and leaves the caller to carry on.
"""

import asyncio
from uuid import uuid4

import pytest

from vibey.infrastructure.notify import DesktopNotifier, NotificationEvent, NotificationKind


def _event() -> NotificationEvent:
    return NotificationEvent(
        kind=NotificationKind.PHASE_TRANSITIONED,
        project_id=uuid4(),
        title="Phase Transitioned",
        message="moved",
        payload={},
    )


class _Process:
    def __init__(self, returncode: int, *, hangs: bool = False) -> None:
        self.returncode = returncode
        self._hangs = hangs

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hangs:
            raise TimeoutError
        return b"", b"Cannot autolaunch D-Bus without X11 $DISPLAY"


def test_a_host_without_notify_send_answers_false(monkeypatch: pytest.MonkeyPatch) -> None:
    async def missing(*args: object, **kwargs: object) -> _Process:
        raise FileNotFoundError("notify-send")

    monkeypatch.setattr("asyncio.create_subprocess_exec", missing)
    assert asyncio.run(DesktopNotifier(platform_override="linux").notify(_event())) is False


def test_notify_send_with_no_session_bus_answers_false(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_bus(*args: object, **kwargs: object) -> _Process:
        return _Process(returncode=1)

    monkeypatch.setattr("asyncio.create_subprocess_exec", no_bus)
    assert asyncio.run(DesktopNotifier(platform_override="linux").notify(_event())) is False


def test_notify_send_that_hangs_answers_false(monkeypatch: pytest.MonkeyPatch) -> None:
    async def hangs(*args: object, **kwargs: object) -> _Process:
        return _Process(returncode=0, hangs=True)

    monkeypatch.setattr("asyncio.create_subprocess_exec", hangs)
    assert asyncio.run(DesktopNotifier(platform_override="linux").notify(_event())) is False
