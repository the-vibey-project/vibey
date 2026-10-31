# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The managed hooks take the `vibey_gh` source to run from local git config only (#1292).

They used to read `[install] self_source` from the tracked `.vibey-gh.toml` and default to
`.`, so a branch that added a root `pyproject.toml` named `vibey-gh` beside a `vibey_gh/`
directory had its own code executed by the developer's commit and push hooks.

Real git and the real rendered hooks, with every `GIT_*` variable scrubbed and the global and
system configs ignored (a hook exports `GIT_DIR`; see test_githooks_in_a_worktree). Each
self-hosted copy is a canary: a `vibey_gh/cli.py` that appends to a log when it is imported.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vibey_gh.config import GhConfig
from vibey_gh.hooks_self_source import KEY
from vibey_gh.install import HOOKS, TEMPLATES, render_hook

STUB_VIBEY_GH = "#!/bin/sh\ncase \"$1\" in trailer-key) echo Made-With;; trailer) echo 'Made-With: x';; esac\nexit 0\n"


def env_for(bin_dir: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("_VIBEY_GH_SELF", None)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def git(cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


def function_text(hook: str) -> str:
    text = (TEMPLATES / hook).read_text(encoding="utf-8")
    start = text.index("vibey_gh_self() {")
    return text[start : text.index("\n}\n", start) + 3]


def canary(root: Path, log: Path) -> None:
    """A foreign branch's own `vibey-gh` source: importing its cli proves it was run."""
    (root / "pyproject.toml").write_text('[project]\nname = "vibey-gh"\n', encoding="utf-8")
    (root / "vibey_gh").mkdir()
    (root / "vibey_gh" / "__init__.py").write_text("", encoding="utf-8")
    (root / "vibey_gh" / "cli.py").write_text(
        f"open({str(log)!r}, 'a').write('ran\\n')\n", encoding="utf-8"
    )


@pytest.fixture
def clone(tmp_path: Path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "vibey-gh").write_text(STUB_VIBEY_GH, encoding="utf-8")
    (bin_dir / "vibey-gh").chmod(0o755)
    env = env_for(bin_dir)
    root = tmp_path / "clone"
    root.mkdir()
    assert git(root, env, "init", "-q", ".").returncode == 0
    git(root, env, "config", "user.email", "t@example.com")
    git(root, env, "config", "user.name", "t")
    return root, env, tmp_path / "canary.log"


def self_dir(root: Path, env: dict[str, str], hook: str = "pre-push") -> str:
    script = f"{function_text(hook)}\nvibey_gh_self\n"
    done = subprocess.run(
        ["sh", "-c", script], cwd=root, env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.mark.parametrize("hook", ["pre-push", "commit-msg"])
def test_a_branch_with_its_own_vibey_gh_is_not_chosen_when_the_key_is_unset(clone, hook):
    root, env, log = clone
    canary(root, log)  # the issue's exact repro: a root pyproject plus vibey_gh/
    assert self_dir(root, env, hook) == ""


def test_a_branch_cannot_name_its_own_source_in_the_tracked_file(clone):
    root, env, log = clone
    (root / ".vibey-gh.toml").write_text('[install]\nself_source = "evil"\n', encoding="utf-8")
    (root / "evil").mkdir()
    canary(root / "evil", log)
    assert self_dir(root, env) == ""


@pytest.mark.parametrize("hook", ["pre-push", "commit-msg"])
def test_a_local_key_keeps_self_hosting_working(clone, hook):
    root, env, log = clone
    (root / "tool").mkdir()
    canary(root / "tool", log)
    assert git(root, env, "config", "--local", KEY, "tool").returncode == 0
    assert self_dir(root, env, hook) == "tool"


@pytest.mark.parametrize("value", ["/abs/path", "../x", "a/../b"])
def test_an_absolute_or_escaping_local_value_is_refused(clone, value):
    root, env, log = clone
    canary(root, log)
    git(root, env, "config", "--local", KEY, value)
    assert self_dir(root, env) == ""


def test_a_local_value_that_is_not_the_tool_is_refused(clone):
    root, env, _ = clone
    (root / "tool").mkdir()
    git(root, env, "config", "--local", KEY, "tool")
    assert self_dir(root, env) == ""  # no pyproject, no vibey_gh/


def test_the_two_hooks_carry_the_same_function_and_neither_reads_the_tracked_file():
    assert function_text("pre-push") == function_text("commit-msg")
    body = function_text("pre-push")
    assert "git config --local --get vibey-gh.self-source" in body
    assert "sed " not in body and "return 0\n" in body
    assert "dir=." not in body


def test_the_key_spelling_is_a_valid_git_variable_and_matches_the_templates(clone):
    root, env, _ = clone
    assert KEY == "vibey-gh.self-source"
    assert all(KEY in function_text(hook) for hook in HOOKS)
    assert git(root, env, "config", "--local", KEY, "x").returncode == 0
    # The underscore spelling the issue first proposed is rejected by git itself.
    assert git(root, env, "config", "--local", "vibey-gh.self_source", "x").returncode != 0


def test_a_linked_worktree_reads_the_clones_key(clone):
    root, env, log = clone
    (root / "tool").mkdir()
    canary(root / "tool", log)
    (root / "README").write_text("x", encoding="utf-8")
    git(root, env, "add", "-A")
    assert git(root, env, "commit", "-qm", "base").returncode == 0
    git(root, env, "config", "--local", KEY, "tool")
    worktree = root.parent / "wt"
    assert git(root, env, "worktree", "add", "-q", str(worktree), "-b", "other").returncode == 0
    assert (worktree / "tool" / "vibey_gh").is_dir()
    assert self_dir(worktree, env) == "tool"


def install_hook(root: Path, env: dict[str, str], hook: str) -> None:
    cfg = GhConfig(root=root)
    (root / ".githooks").mkdir()
    path = root / ".githooks" / hook
    path.write_text(render_hook(TEMPLATES / hook, cfg), encoding="utf-8")
    path.chmod(0o755)
    git(root, env, "config", "core.hooksPath", ".githooks")


def test_a_real_commit_runs_a_foreign_branchs_vibey_gh_only_when_the_operator_set_the_key(clone):
    root, env, log = clone
    canary(root, log)
    install_hook(root, env, "commit-msg")
    (root / "a.txt").write_text("a", encoding="utf-8")
    git(root, env, "add", "a.txt")
    done = git(root, env, "commit", "-qm", "feat: one")
    assert done.returncode == 0, done.stderr
    assert not log.exists(), "the branch's own vibey_gh ran with the key unset"

    git(root, env, "config", "--local", KEY, ".")
    (root / "b.txt").write_text("b", encoding="utf-8")
    git(root, env, "add", "b.txt")
    done = git(root, env, "commit", "-qm", "feat: two")
    assert done.returncode == 0, done.stderr
    assert log.exists(), "the operator's own opt-in no longer runs the checkout's source"
