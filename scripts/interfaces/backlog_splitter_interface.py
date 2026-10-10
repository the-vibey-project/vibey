# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/backlog_splitter.py` implements. Interfaces declare; they never consume.

The *sink* is the one place the splitter writes to the forge. The *splitter* decides which
issues are too large to hand an agent and cuts them along the structure they already have.
"""

from typing import Any, Protocol


class SplitSinkInterface(Protocol):
    """The forge, written to: only issues, their labels, and one comment on the parent."""

    def split_children(self, label: str) -> list[dict[str, Any]]:
        """Every issue, open or closed, carrying `label`: number, body."""
        ...

    def ensure_label(self, name: str, color: str, description: str) -> None:
        """Create the label if it is missing; leave it alone if it exists."""
        ...

    def create_issue(self, title: str, body: str, labels: list[str]) -> dict[str, Any]:
        """File one issue; return its `id` and `number`."""
        ...

    def link_sub_issue(self, parent: int, child_id: int) -> bool:
        """Attach the child to the parent as a sub-issue; False when the forge declines."""
        ...

    def mark_parent(self, parent: int, label: str, comment: str) -> None:
        """Label the parent as split and comment the children on it."""
        ...


class BacklogSplitterInterface(Protocol):
    """Cuts an issue too large for an agent into the slices its own structure names."""

    def outline(self, body: str) -> list[tuple[str, str]]:
        """The (title, detail) slices a body's task list, numbered steps or sections name;
        empty when it has none to split on."""
        ...

    def parents(self) -> list[dict[str, Any]]:
        """The open issues that are too large and may be split, oldest first."""
        ...

    def run(self, *, apply: bool) -> list[str]:
        """Plan every split and, when `apply`, file it; the report, line by line."""
        ...
