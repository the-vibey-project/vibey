# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A desktop notification's text is data, never AppleScript.

The notifier used to build `display notification "<message>" with title "<title>"` and
hand it to `osascript -e`, escaping only `"`. The text comes from the model (a DESIGN
question's summary) and from gate output, so a message ending `\\" & (do shell script
...) --` closed the string with its own backslash, ran the command, and commented out
the rest of the line. Reproduced in review, and below against the real `osascript`.

The title and message now travel as `osascript` arguments to a fixed `on run argv`
script, and the process starts from the system basics, not the worker's environment.
"""

import asyncio
import shutil
import sys
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.infrastructure.notify import DesktopNotifier, NotificationEvent, NotificationKind
from vibey.infrastructure.notify.desktop import APPLESCRIPT
from vibey.infrastructure.notify.interfaces import DesktopNotifierInterface


def _payload(marker: Path) -> str:
    """The reviewer's shape: close the string, run a shell command, comment out the rest.
    The command is spelled in character ids so it needs no quote of its own."""
    codes = ", ".join(str(ord(c)) for c in f"touch {marker}")
    return 'done\\" & (do shell script (character id {' + codes + "})) --"


def _event(*, title: str = "Phase Transitioned", message: str = "moved") -> NotificationEvent:
    return NotificationEvent(
        kind=NotificationKind.PHASE_TRANSITIONED,
        project_id=uuid4(),
        title=title,
        message=message,
        payload={},
    )


def test_the_script_is_fixed_and_the_text_travels_as_arguments(tmp_path: Path) -> None:
    message = _payload(tmp_path / "pwned")
    title = 'x" & (do shell script "id") --'

    cmd = DesktopNotifier(platform_override="darwin")._build_command(
        _event(title=title, message=message)
    )

    assert APPLESCRIPT == (
        "on run argv",
        "display notification (item 2 of argv) with title (item 1 of argv) "
        "sound name (item 3 of argv)",
        "end run",
    )
    assert cmd == [
        "osascript",
        "-e",
        APPLESCRIPT[0],
        "-e",
        APPLESCRIPT[1],
        "-e",
        APPLESCRIPT[2],
        "--",
        f"vibey: {title}",
        message,
        "Ping",
    ]
    statements = [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "-e"]
    assert not any("do shell script" in statement for statement in statements)


def test_notify_send_takes_the_text_verbatim_after_its_option_terminator() -> None:
    cmd = DesktopNotifier(platform_override="linux")._build_command(
        _event(title="t", message='--icon=/etc/passwd "quoted"')
    )
    assert cmd == ["notify-send", "--", "vibey: t", '--icon=/etc/passwd "quoted"']


@pytest.mark.skipif(
    sys.platform != "darwin" or shutil.which("osascript") is None,
    reason="the injection is into AppleScript, which only macOS runs",
)
def test_the_reviewers_payload_runs_no_command_through_the_real_osascript(tmp_path: Path) -> None:
    marker = tmp_path / "pwned"

    delivered = asyncio.run(
        DesktopNotifier(platform_override="darwin").notify(_event(message=_payload(marker)))
    )

    assert delivered is True
    assert not marker.exists()


def test_the_notifier_process_starts_from_the_system_basics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://vibey:secret@db/vibey")
    monkeypatch.setenv("PGPASSWORD", "secret")
    monkeypatch.setenv("GH_TOKEN", "ghp_secret")
    seen: dict[str, object] = {}

    class FakeProcess:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def fake_create(*args: object, **kwargs: object) -> FakeProcess:
        seen.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", fake_create)

    assert asyncio.run(DesktopNotifier(platform_override="linux").notify(_event())) is True

    env = seen["env"]
    assert isinstance(env, dict)
    assert "PATH" in env
    assert not {n for n in env if n.startswith(("VIBEY_", "PG"))}
    assert "GH_TOKEN" not in env


def test_the_notifier_declares_its_interface() -> None:
    assert isinstance(DesktopNotifier(), DesktopNotifierInterface)
