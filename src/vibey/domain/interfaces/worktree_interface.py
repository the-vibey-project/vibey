# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for naming a project's BUILD worktrees and branches, and for the record
that ties a branch to the project that created it (`domain/worktree.py`, ADR-0008).
Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class WorktreeNamingInterface(Protocol):
    """Where one project's BUILD worktrees live and what their branches are called, for
    one cycle. Pure: the same project and cycle always name the same things."""

    @property
    def project_id(self) -> UUID:
        """The project every name here belongs to."""
        ...

    @property
    def cycle(self) -> int:
        """The cycle every name here belongs to."""
        ...

    @property
    def scope(self) -> str:
        """The project's short token in names: the first eight hex digits of its id."""
        ...

    @property
    def managed_root(self) -> str:
        """The directory, relative to the repository, holding this cycle's worktrees."""
        ...

    @property
    def integration_branch(self) -> str:
        """The branch `build.integrate` merges this cycle's items into."""
        ...

    def worktree_subpath(self, item_id: str) -> str:
        """An item's worktree, relative to the repository. Raises ValueError for an
        invalid item id."""
        ...

    def branch(self, item_id: str) -> str:
        """An item's branch. Raises ValueError for an invalid item id."""
        ...

    def legacy_branch(self, item_id: str) -> str:
        """The cycle-keyed name the item's branch had before names carried the project.
        Never created, never adopted: only recognised, so an old job's recorded base can
        be read as this project's integration branch."""
        ...

    def resolve_base(self, ref: str) -> str:
        """The base an item branch is cut from: `ref`, except the pre-scoping cycle-keyed
        integration branch, which reads as this project's own."""
        ...

    def is_managed(self, ref: str) -> bool:
        """Whether `ref` is in the namespace vibey names its BUILD branches in, and so
        must be proved this project's before it is used."""
        ...


@runtime_checkable
class BranchOwnershipInterface(Protocol):
    """What a repository records about who created one BUILD branch, and from where."""

    @property
    def branch(self) -> str:
        """The branch the record is about."""
        ...

    @property
    def project_id(self) -> str | None:
        """The project recorded as the branch's creator, as written; `None` when nothing
        was recorded."""
        ...

    @property
    def base(self) -> str | None:
        """The commit the branch was cut from, as recorded; `None` when nothing was."""
        ...

    def verify(self, project_id: UUID) -> str:
        """The recorded base commit when the record names `project_id` and a base. Raises
        `ForeignBranchRefused` otherwise."""
        ...
