# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from qwenloop.infrastructure.desktop_notifications import DesktopNotifier


@pytest.mark.asyncio
async def test_macos_notification_passes_text_as_argv_data() -> None:
    commands: list[list[str]] = []
    notifier = DesktopNotifier(
        executor=lambda command: commands.append(command) or True,
        platform_override="darwin",
    )

    assert await notifier.notify('Run "done"', 'line one\nline "two"')
    assert commands[0][:1] == ["osascript"]
    assert commands[0][-4:] == [
        "--",
        'vibey: Run "done"',
        'line one\nline "two"',
        "Ping",
    ]
    assert "do shell script" not in " ".join(commands[0])


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
    assert commands == [["notify-send", "--", "vibey: Title", "message"]]


def test_linux_notification_uses_configured_icon() -> None:
    notifier = DesktopNotifier(platform_override="linux", icon_path="/icons/krypton.png")
    assert notifier._build_command("Title", "message") == [
        "notify-send",
        "--icon",
        "/icons/krypton.png",
        "--",
        "vibey: Title",
        "message",
    ]


def test_configured_icon_uses_terminal_notifier_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "qwenloop.infrastructure.desktop_notifications.shutil.which",
        lambda _: "/bin/terminal-notifier",
    )
    notifier = DesktopNotifier(platform_override="darwin", icon_path="/icons/krypton.png")
    assert notifier._build_command("Title", "message") == [
        "terminal-notifier",
        "-title",
        "vibey: Title",
        "-message",
        "message",
        "-sound",
        "Ping",
        "-appIcon",
        "/icons/krypton.png",
    ]


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
    command = notifier._build_command("Title", "message")
    assert command[-1] == "Glass"
    assert "sound name (item 3 of argv)" in " ".join(command)
