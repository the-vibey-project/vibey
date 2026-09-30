# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure naming rules for BUILD work-item worktrees (M6 task 6.2), scoped per project.

No I/O here -- just the deterministic path/branch scheme the infrastructure worktree
manager uses, kept pure so the manager, the integration branch, the status document and
the delivery bridge never disagree about where a work item's worktree lives or what its
branch is called. Returns relative path strings rather than `pathlib.Path`: domain/
forbids pathlib (test_domain_purity.py), so joining onto a repo root is infrastructure's
job.

**Names carry the project, not only the cycle.** They used to be
`.vibey/worktrees/<cycle>/<item>` on branch `vibey/<cycle>/<item>`, and every project in
one repository shares that repository's refs -- including every delivery the triaged
bridge runs in a linked worktree of the main checkout. A delivery in cycle 1 therefore
found an unrelated August project's `vibey/1/ws` and `vibey/1/integration`, built on that
history, and would have published it. The scheme is now
`.vibey/worktrees/<scope>/<cycle>/<item>` on `<namespace>/<scope>/<cycle>/<item>`, where
`scope` is the first eight hex digits of the project id. Eight digits make a collision
unlikely, not impossible, so the name is not the only defence: every branch BUILD creates
also records the full project id and its base commit (`BranchOwnership`), and a branch
whose record does not name this project is refused, never adopted.
"""

import re
from dataclasses import dataclass
from uuid import UUID

from vibey.domain.errors import ForeignBranchRefused
from vibey.domain.interfaces.worktree_interface import (
    BranchOwnershipInterface,
    WorktreeNamingInterface,
)

_ITEM_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,63}$")
_NAMESPACE_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{0,31}$")

DEFAULT_BRANCH_NAMESPACE = "vibey"
"""The first segment of every BUILD branch name."""

WORKTREE_ROOT = ".vibey/worktrees"
"""Where BUILD worktrees live, relative to the project's repository."""

INTEGRATION_ITEM_ID = "integration"
"""The reserved item id of the branch `build.integrate` merges items into."""

SCOPE_LENGTH = 8
"""How many leading hex digits of the project id name it in paths and branches -- the same
short id the delivery bridge puts in its pull-request branch (`delivery/<issue>-<id8>`)."""


# Module-level rather than a method (ADR-0016's written reason): it predates the naming
# class, validates an id before any name exists, and is imported by callers and tests
# that hold no project. `WorktreeNaming` calls it before minting a name.
def validate_item_id(item_id: str) -> None:
    if not _ITEM_ID_RE.match(item_id):
        raise ValueError(
            f"invalid work item id {item_id!r}: must be 1-64 chars, "
            "lowercase alphanumeric and hyphens, starting with alphanumeric"
        )


@dataclass(frozen=True, slots=True)
class WorktreeNaming:
    """One project's BUILD worktree and branch names for one cycle."""

    project_id: UUID
    cycle: int
    namespace: str = DEFAULT_BRANCH_NAMESPACE

    def __post_init__(self) -> None:
        if isinstance(self.cycle, bool) or not isinstance(self.cycle, int) or self.cycle < 1:
            raise ValueError(f"invalid cycle {self.cycle!r}: must be a whole number from 1")
        if not _NAMESPACE_RE.match(self.namespace):
            raise ValueError(
                f"invalid branch namespace {self.namespace!r}: must be 1-32 chars, "
                "lowercase alphanumeric and hyphens, starting with alphanumeric"
            )

    @property
    def scope(self) -> str:
        return self.project_id.hex[:SCOPE_LENGTH]

    @property
    def managed_root(self) -> str:
        return f"{WORKTREE_ROOT}/{self.scope}/{self.cycle}"

    @property
    def integration_branch(self) -> str:
        return self.branch(INTEGRATION_ITEM_ID)

    def worktree_subpath(self, item_id: str) -> str:
        validate_item_id(item_id)
        return f"{self.managed_root}/{item_id}"

    def branch(self, item_id: str) -> str:
        validate_item_id(item_id)
        return f"{self.namespace}/{self.scope}/{self.cycle}/{item_id}"

    def legacy_branch(self, item_id: str) -> str:
        validate_item_id(item_id)
        return f"{self.namespace}/{self.cycle}/{item_id}"

    def resolve_base(self, ref: str) -> str:
        # A job enqueued before names carried the project recorded its base as the
        # cycle-keyed integration branch. That name is shared by every project in the
        # repository, so it is read as this project's own integration branch -- never
        # looked up as written.
        if ref == self.legacy_branch(INTEGRATION_ITEM_ID):
            return self.integration_branch
        return ref

    def is_managed(self, ref: str) -> bool:
        return ref.startswith(f"{self.namespace}/")


@dataclass(frozen=True, slots=True)
class BranchOwnership:
    """What the repository records about who created a BUILD branch, and from where.

    Recorded before the branch exists, so a create killed half-way leaves a branch that
    still proves whose it is; read back before a branch is reused, based on, or merged.
    Values are kept as written: a malformed record is a foreign one, not an error."""

    branch: str
    project_id: str | None
    base: str | None

    def verify(self, project_id: UUID) -> str:
        if self.project_id is None:
            raise ForeignBranchRefused(self.branch, project_id, "it records no creating project")
        if self.project_id != str(project_id):
            raise ForeignBranchRefused(
                self.branch, project_id, f"it records project {self.project_id} as its creator"
            )
        if not self.base:
            raise ForeignBranchRefused(self.branch, project_id, "it records no base commit")
        return self.base


# The annotations are load-bearing: a `runtime_checkable` Protocol only checks member
# names at runtime, so these assignments are what make `mypy --strict` verify that the
# classes actually satisfy their declared seams (ADR-0016).
_NAMING_SEAM: type[WorktreeNamingInterface] = WorktreeNaming
_OWNERSHIP_SEAM: type[BranchOwnershipInterface] = BranchOwnership
