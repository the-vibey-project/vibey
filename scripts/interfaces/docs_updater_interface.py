# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/docs_updater.py` implements. Interfaces declare; they never consume.

The *runs* source lists a workflow's runs on a branch. The *book channel* says whether the
published develop book, site and paper PDF are behind the newest release they can be built from.
"""

from typing import Any, Protocol


class WorkflowRunsInterface(Protocol):
    """The forge's run history, read-only."""

    def runs(self, workflow: str, branch: str) -> list[dict[str, Any]]:
        """Recent runs, newest first: databaseId, conclusion, headSha, createdAt."""
        ...


class BookChannelInterface(Protocol):
    """Whether the published channel needs rebuilding, and how far it lags the branch."""

    def assess(self, tip: str) -> dict[str, Any]:
        """`rebuild_from` (a release run id, or None), `built_from` and a `report` line."""
        ...
