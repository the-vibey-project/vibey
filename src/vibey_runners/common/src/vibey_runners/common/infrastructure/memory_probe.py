# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The family's one reading of how much physical memory this machine has (#383).

vibey-gh's fit calculus and qwenloop's default-model selection both need it, so it lives
here once (sub-doctrine 10.e). Arch Linux states it in /proc/meminfo and macOS answers
`sysctl -n hw.memsize` (sub-doctrine 8.h). The command runner and the file reader are
declared seams (9.b): a test hands in exact output instead of patching anything.
"""

from __future__ import annotations

import subprocess  # nosec B404 - one fixed argv, below
import sys
from collections.abc import Callable

from vibey_runners.common.infrastructure.interfaces.memory_probe_interface import (
    MemoryProbeInterface,
)

#: Where Linux states its memory. A default, not a constant (12.c).
LINUX_MEMINFO_PATH = "/proc/meminfo"
#: How macOS states its memory, in bytes.
DARWIN_MEMSIZE_ARGV: tuple[str, ...] = ("sysctl", "-n", "hw.memsize")
#: How long that command may take before the machine counts as unreadable.
DEFAULT_COMMAND_TIMEOUT_SECONDS = 20.0


class MemoryProbe(MemoryProbeInterface):
    """Reads this machine's physical memory, or says it could not (None, never a guess)."""

    def __init__(
        self,
        *,
        platform_name: str = "",
        runner: Callable[[tuple[str, ...]], str] | None = None,
        reader: Callable[[str], str | None] | None = None,
        meminfo_path: str = LINUX_MEMINFO_PATH,
        command_timeout_seconds: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    ) -> None:
        self._platform = platform_name or sys.platform
        self._runner = self._run_command if runner is None else runner
        self._reader = self._read_text if reader is None else reader
        self._meminfo_path = meminfo_path
        self._timeout = command_timeout_seconds

    def total_bytes(self) -> int | None:
        if self._platform.startswith("linux"):
            return self._linux_total()
        if self._platform == "darwin":
            return self._darwin_total()
        return None

    def _darwin_total(self) -> int | None:
        raw = self._runner(DARWIN_MEMSIZE_ARGV).strip()
        if not raw.isdigit() or int(raw) <= 0:
            return None
        return int(raw)

    def _linux_total(self) -> int | None:
        text = self._reader(self._meminfo_path)
        if text is None:
            return None
        for line in text.splitlines():
            key, _, rest = line.partition(":")
            if key.strip() != "MemTotal":
                continue
            parts = rest.split()
            if not parts or not parts[0].isdigit():
                return None
            value = int(parts[0])
            if len(parts) > 1 and parts[1].lower() == "kb":
                value *= 1024
            return value if value > 0 else None
        return None

    def _run_command(self, argv: tuple[str, ...]) -> str:
        """stdout of a finished command, or "" for any failure (never raises)."""
        try:
            completed = subprocess.run(  # nosec B603 - fixed argv, no shell
                list(argv),
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return completed.stdout if completed.returncode == 0 else ""

    @staticmethod
    def _read_text(path: str) -> str | None:
        """The whole file, or None when this machine has no such file."""
        try:
            with open(path, encoding="utf-8") as handle:
                return handle.read()
        except OSError:
            return None
