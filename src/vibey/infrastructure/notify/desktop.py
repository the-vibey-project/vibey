# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Desktop notification sender for interactive terminals.

A notification's title and message are untrusted text: they come from the model (a
DESIGN interview's summary) and from gate output. They are passed to the platform's
notifier as ARGUMENTS and never become part of a script. On macOS that is a fixed
`on run argv` AppleScript reading `item N of argv`; interpolating the text into
`osascript -e` source, with only `"` escaped, let a message ending `\\" & (do shell
script ...) --` run a shell command. `notify-send` gets its text after `--`, so text
beginning with `-` is not read as an option.

The notifier process starts from the system basics (`SYSTEM_ENVIRONMENT`), never a copy
of the worker's environment.

Declared by `interfaces/desktop_interface.py` (ADR-0016).
"""

import asyncio
import sys
from collections.abc import Callable
from contextlib import suppress

from vibey.infrastructure.notify.events import NotificationEvent
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT, ChildEnvironment
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface

# The whole AppleScript, fixed. The title, message and sound are its run handler's
# arguments, so no text of theirs is ever parsed as AppleScript.
APPLESCRIPT: tuple[str, ...] = (
    "on run argv",
    "display notification (item 2 of argv) with title (item 1 of argv) sound name (item 3 of argv)",
    "end run",
)


class DesktopNotifier:
    """Shows one notification on the operator's desktop. Declared by
    `interfaces/desktop_interface.py`."""

    def __init__(
        self,
        *,
        executor: Callable[[list[str]], bool] | None = None,
        platform_override: str | None = None,
        sound_name: str = "Ping",
        environment: ChildEnvironmentInterface | None = None,
    ) -> None:
        self._executor = executor
        self._platform = platform_override or sys.platform
        self._sound_name = sound_name
        self._environment = (
            ChildEnvironment(SYSTEM_ENVIRONMENT) if environment is None else environment
        )

    async def notify(self, event: NotificationEvent) -> bool:
        cmd = self._build_command(event)
        if not cmd:
            return False

        if self._executor is not None:
            return self._executor(cmd)

        with suppress(Exception):
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._environment.build(),
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return proc.returncode == 0
        return False

    def _build_command(self, event: NotificationEvent) -> list[str]:
        title = f"vibey: {event.title}"
        if self._platform == "darwin":
            statements = [part for line in APPLESCRIPT for part in ("-e", line)]
            return ["osascript", *statements, "--", title, event.message, self._sound_name]
        elif self._platform.startswith("linux"):
            return ["notify-send", "--", title, event.message]
        return []
