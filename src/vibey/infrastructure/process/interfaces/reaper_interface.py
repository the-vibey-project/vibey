# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for killing a spawned process and reaping it within a bound.

Mirrors `vibey/infrastructure/process/reaper.py` (ADR-0016). Interfaces declare;
they never consume.
"""

import asyncio
from typing import Protocol, runtime_checkable


@runtime_checkable
class ProcessReaperInterface(Protocol):
    """Kills the process group a spawned process leads, and reaps it within a bound.

    The process must have been started with `start_new_session=True`, so that it leads
    a process group of its own. The group kill then reaches everything the process
    started inside that group.
    """

    @property
    def grace_seconds(self) -> float:
        """The longest `kill_and_reap` waits for the killed process to be reaped."""
        ...

    async def kill_and_reap(self, process: asyncio.subprocess.Process) -> bool:
        """SIGKILL the group `process` leads, then wait at most `grace_seconds` for it.

        True when the process was reaped in time. False when the wait gave up, which is
        logged. A group that is already gone is not an error.
        """
        ...
