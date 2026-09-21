# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure values shared by the OpenCode adapter."""

from dataclasses import dataclass
from enum import StrEnum

DONE_MARKER = "OPENCODELOOP_TASK_FULLY_COMPLETE"


class RunStatus(StrEnum):
    """Terminal and in-flight states persisted by the process adapter."""

    ACTIVE = "active"
    FINISHED = "finished"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class RunResult:
    """The process outcome without any filesystem or subprocess concerns."""

    status: RunStatus
    returncode: int
    session_id: str | None = None
    detail: str = ""

    @property
    def succeeded(self) -> bool:
        """Whether OpenCode reached a clean terminal state."""
        return self.status is RunStatus.FINISHED and self.returncode == 0
