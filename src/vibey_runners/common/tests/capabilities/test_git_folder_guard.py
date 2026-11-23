# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether a path is the marketplace root's `.git` or inside it, decided by file identity first
and by case-folded name second, so `.GIT`, `.Git` or any other alias of the same folder is
refused on every file system (the second automated security review)."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.git_folder_guard_interface import (
    GitFolderGuardInterface,
)


def _aliasing(alias: Path, real: Path) -> Callable[[Path], os.stat_result]:
    """A stat seam that reports `alias` as the same file as `real`, as a case-insensitive or
    normalising file system would, on any operating system."""

    def fake(path: Path) -> os.stat_result:
        return os.stat(real if path == alias else path)

    return fake


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / ".git" / "objects").mkdir(parents=True)
    (tmp_path / "plugins" / "lint").mkdir(parents=True)
    return tmp_path


def test_the_git_folder_and_what_it_holds_are_inside(root: Path) -> None:
    guard = GitFolderGuard()
    assert guard.inside(root, root / ".git")
    assert guard.inside(root, root / ".git" / "objects")
    assert not guard.inside(root, root / "plugins" / "lint")
    assert not guard.inside(root, root)
    assert isinstance(guard, GitFolderGuardInterface)


def test_a_path_outside_the_root_is_not_inside(root: Path, tmp_path: Path) -> None:
    assert not GitFolderGuard().inside(root / "plugins", tmp_path / ".git")


def test_an_alias_with_the_same_identity_is_inside_whatever_its_name(root: Path) -> None:
    alias = root / "plugins"
    guard = GitFolderGuard(stat=_aliasing(alias, root / ".git"))
    assert guard.inside(root, alias / "lint")
    assert not GitFolderGuard().inside(root, alias / "lint")


@pytest.mark.parametrize("name", [".GIT", ".Git", ".gIt", "．ｇｉｔ"])
def test_a_case_or_width_variant_of_the_name_is_inside(tmp_path: Path, name: str) -> None:
    # No folder is created: the name alone is refused, whatever the file system says.
    assert GitFolderGuard().inside(tmp_path, tmp_path / name / "x")


def test_without_a_root_git_folder_nothing_is_stat_ed_or_refused(tmp_path: Path) -> None:
    (tmp_path / "plugins").mkdir()
    seen: list[Path] = []

    def recording(path: Path) -> os.stat_result:
        seen.append(path)
        return os.stat(path)

    assert not GitFolderGuard(stat=recording).inside(tmp_path, tmp_path / "plugins")
    assert seen == [tmp_path / ".git"]


def test_a_missing_candidate_is_judged_by_its_existing_parents(root: Path) -> None:
    guard = GitFolderGuard(stat=_aliasing(root / "plugins", root / ".git"))
    assert guard.inside(root, root / "plugins" / "not-there" / "SKILL.md")
    assert not GitFolderGuard().inside(root, root / "plugins" / "not-there")


def test_a_deeper_git_name_counts_only_when_asked(root: Path) -> None:
    deep = root / "plugins" / "lint" / ".GIT" / "x"
    assert not GitFolderGuard().inside(root, deep)
    assert GitFolderGuard().inside(root, deep, any_depth=True)


def test_a_real_symlink_alias_to_the_git_folder_is_inside(root: Path) -> None:
    alias = root / "plugins" / "alias"
    try:
        alias.symlink_to(root / ".git", target_is_directory=True)
    except (OSError, NotImplementedError):  # pragma: no cover - only where links cannot be made
        pytest.skip("this operating system cannot create a symlink here")
    # Unresolved on purpose: the name says nothing, the identity says .git.
    assert GitFolderGuard().inside(root, alias / "objects")
