# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from uuid import UUID

import pytest

from vibey.domain.errors import ForeignBranchRefused
from vibey.domain.interfaces.worktree_interface import (
    BranchOwnershipInterface,
    WorktreeNamingInterface,
)
from vibey.domain.worktree import (
    BranchOwnership,
    WorktreeNaming,
    validate_item_id,
)

PROJECT = UUID("893c4fc1-542e-411e-a10a-3aef784b1540")
OTHER = UUID("11111111-2222-3333-4444-555555555555")


def test_validate_item_id_accepts_lowercase_alphanumeric_and_hyphens() -> None:
    validate_item_id("item-014")
    validate_item_id("a")
    validate_item_id("skeleton")


@pytest.mark.parametrize("bad", ["", "Item-1", "item_1", "-item", "it/em", "a" * 65])
def test_validate_item_id_rejects_invalid_ids(bad: str) -> None:
    with pytest.raises(ValueError, match="invalid work item id"):
        validate_item_id(bad)


def test_names_carry_the_project_scope_and_the_cycle() -> None:
    naming = WorktreeNaming(PROJECT, 1)

    assert naming.scope == "893c4fc1"
    assert naming.managed_root == ".vibey/worktrees/893c4fc1/1"
    assert naming.worktree_subpath("ws") == ".vibey/worktrees/893c4fc1/1/ws"
    assert naming.branch("ws") == "vibey/893c4fc1/1/ws"
    assert naming.integration_branch == "vibey/893c4fc1/1/integration"
    assert isinstance(naming, WorktreeNamingInterface)


def test_two_projects_in_cycle_one_never_share_a_name() -> None:
    """The live collision: cycle-keyed names were shared by every project in a repository."""
    ours, theirs = WorktreeNaming(PROJECT, 1), WorktreeNaming(OTHER, 1)

    assert ours.branch("ws") != theirs.branch("ws")
    assert ours.integration_branch != theirs.integration_branch
    assert ours.worktree_subpath("ws") != theirs.worktree_subpath("ws")
    assert ours.managed_root != theirs.managed_root


def test_cycles_of_one_project_never_share_a_name() -> None:
    assert WorktreeNaming(PROJECT, 2).branch("ws") != WorktreeNaming(PROJECT, 1).branch("ws")


def test_the_namespace_is_the_first_segment() -> None:
    assert WorktreeNaming(PROJECT, 1, namespace="build").branch("ws") == "build/893c4fc1/1/ws"


@pytest.mark.parametrize("bad", ["", "Vibey", "vi/bey", "-vibey", "a" * 33])
def test_an_invalid_namespace_is_refused(bad: str) -> None:
    with pytest.raises(ValueError, match="invalid branch namespace"):
        WorktreeNaming(PROJECT, 1, namespace=bad)


@pytest.mark.parametrize("bad", [0, -1, True])
def test_an_invalid_cycle_is_refused(bad: int) -> None:
    with pytest.raises(ValueError, match="invalid cycle"):
        WorktreeNaming(PROJECT, bad)


@pytest.mark.parametrize(
    "mint",
    [
        lambda n: n.worktree_subpath("Bad Id"),
        lambda n: n.branch("Bad Id"),
        lambda n: n.legacy_branch("Bad Id"),
    ],
)
def test_every_name_rejects_an_invalid_item_id(mint: object) -> None:
    with pytest.raises(ValueError, match="invalid work item id"):
        mint(WorktreeNaming(PROJECT, 1))  # type: ignore[operator]


def test_the_legacy_integration_base_reads_as_the_projects_own() -> None:
    """A job enqueued before names carried the project recorded `vibey/<cycle>/integration`
    as its base -- a name every project shares. It is never looked up as written."""
    naming = WorktreeNaming(PROJECT, 1)

    assert naming.legacy_branch("integration") == "vibey/1/integration"
    assert naming.resolve_base("vibey/1/integration") == "vibey/893c4fc1/1/integration"
    assert naming.resolve_base("HEAD") == "HEAD"
    assert naming.resolve_base("develop") == "develop"
    # Another cycle's legacy name is not this cycle's, and is left for the ownership check.
    assert naming.resolve_base("vibey/2/integration") == "vibey/2/integration"


def test_managed_refs_are_the_namespace_s() -> None:
    naming = WorktreeNaming(PROJECT, 1)

    assert naming.is_managed("vibey/1/ws")
    assert naming.is_managed("vibey/11111111/1/integration")
    assert not naming.is_managed("develop")
    assert not naming.is_managed("vibeyish/1/ws")


def test_ownership_naming_this_project_yields_its_base() -> None:
    record = BranchOwnership("vibey/893c4fc1/1/ws", str(PROJECT), "abc123")

    assert record.verify(PROJECT) == "abc123"
    assert isinstance(record, BranchOwnershipInterface)


@pytest.mark.parametrize(
    ("recorded", "base", "reason"),
    [
        (None, "abc123", "records no creating project"),
        (str(OTHER), "abc123", f"records project {OTHER} as its creator"),
        ("not-a-uuid", "abc123", "records project not-a-uuid as its creator"),
        (str(PROJECT), None, "records no base commit"),
        (str(PROJECT), "", "records no base commit"),
    ],
)
def test_ownership_that_does_not_prove_this_project_is_refused(
    recorded: str | None, base: str | None, reason: str
) -> None:
    record = BranchOwnership("vibey/1/ws", recorded, base)

    with pytest.raises(ForeignBranchRefused, match=reason) as refused:
        record.verify(PROJECT)
    assert refused.value.branch == "vibey/1/ws"
    assert refused.value.project_id == PROJECT
    assert refused.value.reason.startswith("it records")
    assert "git branch -m vibey/1/ws" in str(refused.value)
