# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether the pre-commit framework's own hooks are installed in a clone (#1689).

These use real repositories, a plain clone and a linked worktree, because the whole point of
asking git for the common directory is that `.git` is a file in a worktree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vibey_gh import install
from vibey_gh.config import GhConfig
from vibey_gh.hook_inspector import CONFIG, MARKER, STAGES, HookInspector
from vibey_gh.interfaces.hook_inspector_interface import HookInspectorInterface


def git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return done.stdout


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    root = tmp_path / "clone"
    root.mkdir()
    git(root, "init", "-q", "-b", "main", ".")
    git(root, "config", "user.email", "t@example.com")
    git(root, "config", "user.name", "t")
    (root / CONFIG).write_text("repos: []\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "init")
    return root


def write_hook(common: Path, stage: str, text: str) -> None:
    hooks = common / "hooks"
    hooks.mkdir(exist_ok=True)
    (hooks / stage).write_text(text, encoding="utf-8")


def test_the_inspector_honours_its_interface() -> None:
    assert isinstance(HookInspector(), HookInspectorInterface)


def test_a_repository_that_declares_no_framework_is_not_held_to_it(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q", "-b", "main", ".")
    assert HookInspector().stages(GhConfig(root=tmp_path)) == {}
    assert HookInspector().problems(GhConfig(root=tmp_path)) == []


def test_a_directory_that_is_not_a_clone_has_nothing_to_say(tmp_path: Path) -> None:
    (tmp_path / CONFIG).write_text("repos: []\n", encoding="utf-8")
    inspector = HookInspector()
    assert inspector.common_dir(GhConfig(root=tmp_path)) is None
    assert inspector.stages(GhConfig(root=tmp_path)) == {}


def test_git_missing_from_the_machine_says_nothing_rather_than_raising(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("git")

    monkeypatch.setattr(subprocess, "run", refuse)
    assert HookInspector().common_dir(GhConfig(root=clone)) is None


def test_every_stage_is_named_when_none_is_installed(clone: Path) -> None:
    cfg = GhConfig(root=clone)
    assert HookInspector().stages(cfg) == dict.fromkeys(STAGES, "missing")
    problems = HookInspector().problems(cfg)
    assert len(problems) == 3
    assert all("vibey-gh setup" in problem for problem in problems)
    assert any("commit-msg hook is not installed" in problem for problem in problems)


def test_a_framework_hook_is_recognised_by_what_the_framework_writes(clone: Path) -> None:
    common = HookInspector().common_dir(GhConfig(root=clone))
    assert common is not None and common.is_absolute()
    for stage in STAGES:
        write_hook(common, stage, f"#!/usr/bin/env bash\n# File {MARKER}: https://pre-commit.com\n")
    assert HookInspector().stages(GhConfig(root=clone)) == dict.fromkeys(STAGES, "installed")
    assert HookInspector().problems(GhConfig(root=clone)) == []


def test_someone_elses_hook_in_the_slot_is_reported_as_not_the_frameworks(clone: Path) -> None:
    common = HookInspector().common_dir(GhConfig(root=clone))
    assert common is not None
    write_hook(common, "pre-push", "#!/bin/sh\necho mine\n")
    states = HookInspector().stages(GhConfig(root=clone))
    assert states["pre-push"] == "foreign" and states["pre-commit"] == "missing"
    assert any(
        "pre-push hook" in p and "not the pre-commit" in p
        for p in HookInspector().problems(GhConfig(root=clone))
    )


def test_a_hook_that_cannot_be_read_is_not_taken_for_the_frameworks(
    clone: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    common = HookInspector().common_dir(GhConfig(root=clone))
    assert common is not None
    write_hook(common, "pre-commit", MARKER)

    def unreadable(self: Path, *_args: object, **_kwargs: object) -> str:
        raise OSError("denied")

    monkeypatch.setattr(Path, "read_text", unreadable)
    assert HookInspector().stages(GhConfig(root=clone))["pre-commit"] == "foreign"


def test_one_install_covers_a_linked_worktree_and_is_read_from_the_common_directory(
    clone: Path, tmp_path: Path
) -> None:
    worktree = tmp_path / "wt"
    git(clone, "worktree", "add", "-q", "-b", "side", str(worktree))
    assert (worktree / ".git").is_file()  # the case a literal .git/hooks/<stage> gets wrong
    inspector = HookInspector()
    here, there = (
        inspector.common_dir(GhConfig(root=clone)),
        inspector.common_dir(GhConfig(root=worktree)),
    )
    assert here is not None and here == there
    assert inspector.stages(GhConfig(root=worktree)) == dict.fromkeys(STAGES, "missing")
    for stage in STAGES:
        write_hook(here, stage, MARKER)
    assert inspector.stages(GhConfig(root=worktree)) == dict.fromkeys(STAGES, "installed")


def test_installed_names_the_missing_hooks_only_for_a_local_check(clone: Path) -> None:
    cfg = GhConfig(root=clone)
    _, local = install.installed(cfg, local=True)
    _, ci = install.installed(cfg, local=False)
    assert any("framework's pre-push hook is not installed" in p for p in local)
    assert not any("framework" in p for p in ci)
    assert any("core.hooksPath is not .githooks — run `vibey-gh setup`" in p for p in local)


def test_a_quiet_check_stays_fail_open_about_the_frameworks_hooks(clone: Path) -> None:
    cfg = GhConfig(root=clone)
    _, named = install.installed(cfg, local=True)
    _, quiet = install.installed(cfg, local=True, frameworks=False)
    assert any("framework" in p for p in named)
    assert not any("framework" in p for p in quiet)


class _Stop(Exception):
    pass


@pytest.mark.parametrize("flags, frameworks", [([], True), (["--quiet"], False)])
def test_the_pre_push_mode_of_check_does_not_ask_about_the_frameworks_hooks(
    monkeypatch: pytest.MonkeyPatch, flags: list[str], frameworks: bool
) -> None:
    from vibey_gh import cli

    seen: list[bool] = []

    def spy(*_args: object, **kwargs: object) -> tuple[bool, list[str]]:
        seen.append(bool(kwargs["frameworks"]))
        raise _Stop

    monkeypatch.setattr(install, "installed", spy)
    monkeypatch.setattr(cli, "load_config", lambda *a, **k: GhConfig(root=Path.cwd()))
    with pytest.raises(_Stop):
        cli.main(["check", *flags])
    assert seen == [frameworks]
