# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure values shared by the OpenCode adapter."""

import re
from dataclasses import dataclass
from enum import StrEnum

DONE_MARKER = "OPENCODELOOP_TASK_FULLY_COMPLETE"

# A run id becomes exactly one path segment under `.opencodeloop/runs/`. The
# pattern admits letters, digits, dot, underscore and hyphen, and refuses a
# leading dot, so `../..` or `.hidden` can never be constructed from caller
# input. Mirrors the validator every sibling runner ships.
_RUN_ID_PATTERN = re.compile(r"\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class RunId:
    """A validated run identifier that is safe as a single path segment."""

    value: str

    @classmethod
    def parse(cls, raw: str) -> "RunId":
        """Return a validated run id, or raise ValueError naming what is wrong."""
        candidate = raw.strip()
        if not _RUN_ID_PATTERN.match(candidate):
            raise ValueError(
                f"invalid run id {raw!r}: must be 1-128 characters of letters, "
                "digits, '.', '_' or '-', and start with a letter or digit"
            )
        return cls(candidate)


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
