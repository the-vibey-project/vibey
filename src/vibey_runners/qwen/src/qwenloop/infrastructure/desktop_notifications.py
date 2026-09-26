# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Best-effort desktop notifications for local Qwen runs."""

import asyncio
import os
import shutil
import sys
from collections.abc import Callable
from contextlib import suppress

APPLESCRIPT: tuple[str, ...] = (
    "on run argv",
    "display notification (item 2 of argv) with title (item 1 of argv) sound name (item 3 of argv)",
    "end run",
)


class DesktopNotifier:
    """Send lifecycle notifications without making them part of run semantics."""

    def __init__(
        self,
        *,
        executor: Callable[[list[str]], bool] | None = None,
        platform_override: str | None = None,
        enabled: bool = True,
        sound_name: str = "Ping",
        icon_path: str | None = None,
    ) -> None:
        self._executor = executor
        self._platform = platform_override or sys.platform
        self._enabled = enabled
        self._sound_name = sound_name
        self._icon_path = icon_path or os.environ.get("VIBEY_NOTIFICATION_ICON")

    async def notify(self, title: str, message: str) -> bool:
        if not self._enabled:
            return False
        command = self._build_command(title, message)
        if not command:
            return False
        if self._executor is not None:
            return self._executor(command)

        with suppress(Exception):
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(process.communicate(), timeout=5.0)
            return process.returncode == 0
        return False

    def _build_command(self, title: str, message: str) -> list[str]:
        if self._platform == "darwin":
            if self._icon_path and shutil.which("terminal-notifier"):
                return [
                    "terminal-notifier",
                    "-title",
                    f"vibey: {title}",
                    "-message",
                    message,
                    "-sound",
                    self._sound_name,
                    "-appIcon",
                    self._icon_path,
                ]
            statements = [part for line in APPLESCRIPT for part in ("-e", line)]
            return [
                "osascript",
                *statements,
                "--",
                f"vibey: {title}",
                message,
                self._sound_name,
            ]
        if self._platform.startswith("linux"):
            command = ["notify-send"]
            if self._icon_path:
                command.extend(["--icon", self._icon_path])
            return [*command, "--", f"vibey: {title}", message]
        return []
