# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Runs one command with its output bounded and its whole process group killed on a timeout
(SP-LOOPS Task 7 review finding 5).

`subprocess.run(capture_output=True)` holds all of a command's output in memory and, on a timeout,
kills only the direct child. git starts helpers (`git-remote-https`, `ssh`, `index-pack`) that
would keep writing into a staging folder the caller has already removed, and a hostile server can
stream "remote:" lines until the deadline. So the command runs in a session of its own
(`start_new_session`), its stdout and stderr go to unnamed temporary files rather than memory, only
the first `output_bytes` of stdout and the last `output_bytes` of stderr are read back, and the
whole group is sent SIGKILL when the command times out and again (harmlessly) when it ends, so no
helper outlives it. The temporary files still grow on disk for as long as the deadline allows.
Declared by `interfaces/bounded_process_runner_interface.py::BoundedProcessRunnerInterface`.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess  # nosec B404 - a fixed argv, never through a shell
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import IO, Any, Final

OUTPUT_BYTES: Final = 64 * 1024
"""The most of a command's stdout (its start) and stderr (its end) read back."""


class BoundedProcessRunner:
    """Declared by `interfaces/bounded_process_runner_interface.py::BoundedProcessRunnerInterface`."""

    def __init__(
        self,
        *,
        popen: Callable[..., Any] = subprocess.Popen,
        killpg: Callable[[int, int], None] = os.killpg,
        output_bytes: int = OUTPUT_BYTES,
    ) -> None:
        self._popen = popen
        self._killpg = killpg
        self._bytes = output_bytes

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            process = self._popen(  # nosec B603 - a fixed argv, never through a shell
                list(argv),
                env=dict(env),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=out,
                stderr=err,
                start_new_session=True,
            )
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._kill(process.pid)
                process.wait()
                raise
            self._kill(process.pid)  # a helper the command left running goes with it
            return subprocess.CompletedProcess(list(argv), code, self._head(out), self._tail(err))

    def _kill(self, group: int) -> None:
        with contextlib.suppress(ProcessLookupError):  # the group is already gone
            self._killpg(group, signal.SIGKILL)

    def _head(self, stream: IO[bytes]) -> str:
        stream.seek(0)
        return stream.read(self._bytes).decode("utf-8", "replace")

    def _tail(self, stream: IO[bytes]) -> str:
        size = stream.seek(0, os.SEEK_END)
        stream.seek(max(0, size - self._bytes))
        return stream.read().decode("utf-8", "replace")
