# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from qwenloop.infrastructure.desktop_notifications import DesktopNotifier


@pytest.mark.asyncio
async def test_macos_notification_uses_ping_and_escapes_text() -> None:
    commands: list[list[str]] = []
    notifier = DesktopNotifier(
        executor=lambda command: commands.append(command) or True,
        platform_override="darwin",
    )

    assert await notifier.notify('Run "done"', 'line one\nline "two"')
    assert commands == [
        [
            "osascript",
            "-e",
            'display notification "line one\\nline \\"two\\"" with title '
            '"vibey: Run \\"done\\"" sound name "Ping"',
        ]
    ]


@pytest.mark.asyncio
async def test_disabled_notification_does_not_execute() -> None:
    commands: list[list[str]] = []
    notifier = DesktopNotifier(
        executor=lambda command: commands.append(command) or True,
        platform_override="darwin",
        enabled=False,
    )

    assert await notifier.notify("Title", "message") is False
    assert commands == []


@pytest.mark.asyncio
async def test_linux_notification_uses_notify_send() -> None:
    commands: list[list[str]] = []
    notifier = DesktopNotifier(
        executor=lambda command: commands.append(command) or False,
        platform_override="linux",
    )

    assert await notifier.notify("Title", "message") is False
    assert commands == [["notify-send", "vibey: Title", "message"]]


@pytest.mark.asyncio
async def test_unsupported_platform_is_a_no_op() -> None:
    notifier = DesktopNotifier(platform_override="win32")
    assert await notifier.notify("Title", "message") is False


@pytest.mark.asyncio
async def test_subprocess_success_and_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Process:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    process = Process(0)

    async def create_process(*args: object, **kwargs: object) -> Process:
        del args, kwargs
        return process

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    notifier = DesktopNotifier(platform_override="darwin")
    assert await notifier.notify("Title", "message") is True
    process.returncode = 1
    assert await notifier.notify("Title", "message") is False


@pytest.mark.asyncio
async def test_subprocess_error_is_best_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    async def create_process(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise OSError("osascript unavailable")

    monkeypatch.setattr("asyncio.create_subprocess_exec", create_process)
    notifier = DesktopNotifier(platform_override="darwin")
    assert await notifier.notify("Title", "message") is False


def test_notifier_command_can_be_inspected_without_running() -> None:
    notifier = DesktopNotifier(platform_override="darwin", sound_name="Glass")
    assert 'sound name "Glass"' in notifier._build_command("Title", "message")[2]
