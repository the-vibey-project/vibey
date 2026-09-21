# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Best-effort desktop notifications for local Qwen runs."""

import asyncio
import sys
from collections.abc import Callable
from contextlib import suppress


class DesktopNotifier:
    """Send lifecycle notifications without making them part of run semantics."""

    def __init__(
        self,
        *,
        executor: Callable[[list[str]], bool] | None = None,
        platform_override: str | None = None,
        enabled: bool = True,
        sound_name: str = "Ping",
    ) -> None:
        self._executor = executor
        self._platform = platform_override or sys.platform
        self._enabled = enabled
        self._sound_name = sound_name

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
        safe_message = self._escape(message)
        safe_title = self._escape(f"vibey: {title}")
        safe_sound = self._escape(self._sound_name)

        if self._platform == "darwin":
            script = (
                f'display notification "{safe_message}" with title "{safe_title}" '
                f'sound name "{safe_sound}"'
            )
            return ["osascript", "-e", script]
        if self._platform.startswith("linux"):
            return ["notify-send", f"vibey: {title}", message]
        return []

    @staticmethod
    def _escape(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
