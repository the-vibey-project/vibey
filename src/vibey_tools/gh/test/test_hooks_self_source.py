# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh install` copies a declared `[install] self_source` into local git config (#1292)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from vibey_gh import install
from vibey_gh.config import GhConfig, load_config
from vibey_gh.hooks_self_source import KEY, HooksSelfSource
from vibey_gh.interfaces.hooks_self_source_interface import HooksSelfSourceInterface


def run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    run(tmp_path, "init", "-q", ".")
    return tmp_path


def declared(root: Path, value: str = "tool") -> GhConfig:
    return GhConfig(root=root, self_source=value, self_source_declared=True)


def test_the_class_is_its_declared_seam():
    assert isinstance(HooksSelfSource(), HooksSelfSourceInterface)


def test_only_an_explicit_declaration_counts(tmp_path):
    assert load_config(tmp_path).self_source_declared is False
    (tmp_path / ".vibey-gh.toml").write_text('[install]\nself_source = "."\n', encoding="utf-8")
    loaded = load_config(tmp_path)
    assert loaded.self_source == "." and loaded.self_source_declared is True
    assert HooksSelfSource().declared(GhConfig(root=tmp_path)) is None
    assert HooksSelfSource().declared(loaded) == "."


def test_an_undeclared_repository_writes_nothing(root):
    cfg = GhConfig(root=root)
    assert HooksSelfSource().reconcile(cfg) == "unchanged"
    assert HooksSelfSource().local(cfg) is None
    assert HooksSelfSource().problems(cfg) == []


def test_a_declared_value_is_copied_once_into_local_config(root):
    cfg = declared(root)
    assert HooksSelfSource().reconcile(cfg) == "installed"
    assert HooksSelfSource().local(cfg) == "tool"
    assert HooksSelfSource().reconcile(cfg) == "unchanged"
    assert HooksSelfSource().problems(cfg) == []


def test_a_different_local_value_is_kept_and_reported_with_the_command(root):
    run(root, "config", "--local", KEY, "mine")
    cfg = declared(root, "tool dir")
    outcome = HooksSelfSource().reconcile(cfg)
    assert outcome.startswith("differs: kept 'mine'") and "'tool dir'" in outcome
    assert HooksSelfSource().local(cfg) == "mine"
    (problem,) = HooksSelfSource().problems(cfg)
    assert f"git config --local {KEY} 'tool dir'" in problem


def test_a_local_value_the_file_never_declared_is_reported(root):
    run(root, "config", "--local", KEY, "stray")
    (problem,) = HooksSelfSource().problems(GhConfig(root=root))
    assert "declares no [install] self_source" in problem and "--unset" in problem


def test_a_declaration_with_nothing_set_is_reported(root):
    (problem,) = HooksSelfSource().problems(declared(root))
    assert f"{KEY} is not set" in problem and "vibey-gh install" in problem


def test_a_git_that_cannot_write_is_reported_not_raised(root, monkeypatch):
    def refuse(cfg, *args):
        code = 1
        return subprocess.CompletedProcess(["git", *args], code, "", "boom\n")

    monkeypatch.setattr(HooksSelfSource, "_git", staticmethod(refuse))
    assert HooksSelfSource().reconcile(declared(root)) == "failed: boom"


def test_install_writes_the_key_only_with_the_hooks_path(root):
    cfg = declared(root)
    install.install(cfg, hooks_path=False)
    assert HooksSelfSource().local(cfg) is None
    actions = install.install(cfg)
    assert HooksSelfSource().local(cfg) == "tool"
    assert any(a.hook == KEY and a.outcome in {"installed", "unchanged"} for a in actions)


def test_installed_flags_the_key_locally_and_ci_ignores_it(root):
    cfg = declared(root)
    install.install(cfg, hooks_path=False)
    run(root, "config", "core.hooksPath", install.HOOKS_DIR)
    assert install.installed(cfg, local=False)[0] is True
    ok, problems = install.installed(cfg, local=True)
    assert not ok and any(KEY in p for p in problems)
    install.install(cfg)
    assert install.installed(cfg, local=True)[0] is True
