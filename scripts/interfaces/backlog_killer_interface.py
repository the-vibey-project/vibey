# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/backlog_killer.py` implements. Interfaces declare; they never consume.

The *source* reads the open backlog and the open pull requests from the forge. The *killer*
ranks the issues an agent may work and picks this run slot's.
"""

from datetime import datetime
from typing import Any, Protocol


class BacklogSourceInterface(Protocol):
    """The forge, read-only."""

    def open_issues(self) -> list[dict[str, Any]]:
        """Every open issue: number, title, labels, body, createdAt, author."""
        ...

    def open_pull_requests(self) -> list[dict[str, Any]]:
        """Every open pull request: number, title, body."""
        ...


class BacklogKillerInterface(Protocol):
    """Picks one open issue per run slot for the backlog prompt to work."""

    def candidates(self) -> list[dict[str, Any]]:
        """The workable issues, best first. Read-only."""
        ...

    def slot(self, now: datetime) -> int:
        """The run slot `now` falls in: UTC minutes since the epoch over `interval_minutes`."""
        ...

    def slot_start(self, now: datetime) -> datetime:
        """The UTC instant the run slot `now` falls in began."""
        ...

    def seconds_until_next_slot(self, now: datetime) -> int:
        """Whole seconds from `now` to the start of the next run slot; at least one."""
        ...

    def may_chain(self, link: int) -> bool:
        """Whether the run at chain position `link` may start the next one: the declared switch
        is on and the position is below the declared maximum."""
        ...

    def pick(self, now: datetime) -> dict[str, Any] | None:
        """This slot's issue, rotating through the first `window` candidates; None when none."""
        ...

    def brief(self, issue: dict[str, Any] | None) -> str:
        """The pick as the agent's evidence, its body bounded and the cut said out loud."""
        ...
