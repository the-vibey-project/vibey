# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The tracked `.githooks` reach the pre-commit framework from a linked worktree too.

vibey-gh sets `core.hooksPath=.githooks`, so git stops reading the framework's hook
directory. The repository-local shims (`pre-commit`, `commit-msg.local`,
`pre-push.local`) chain back to it, and they used to find it by the literal
`.git/hooks/<stage>`. In a linked worktree `.git` is a FILE, so that path never exists,
and every commit and push from a worktree went out with no local gate and no word said
(#282). The storm runs all development as worktrees, so in practice the gates ran for
almost nothing.

These tests drive the REAL tracked hooks through real `git commit` and `git push` into
a scratch repository with a linked worktree. The rendered vibey-gh hooks come along
unchanged, with a stub `vibey-gh` on PATH that approves, so the chain under test is
the whole one: git -> vibey-gh hook -> shim -> framework-hook.sh -> framework hook. A
fake framework hook stands in for `pre-commit install` and records each stage it runs,
where it ran, whether `GIT_DIR` reached it, and what it read on stdin.

`GIT_DIR` matters as much as the path. git exports it to a linked worktree's hooks and
not to a plain clone's, and the framework passes it to everything it starts. The first
push this fix enabled ran the suite with it set, and a `git init <scratch>` in
`vibey.application.conformance` rewrote the SHARED git config to `core.bare = true`,
which broke the main checkout for every worktree, while its `git commit --allow-empty`
landed on the pushing branch. `framework-hook.sh` now hands the framework a plain
clone's environment, and a test below reproduces that damage and proves it cannot land.

This module's own subprocesses run with every `GIT_*` variable scrubbed and the global
and system git configs ignored, for the same reason: it runs inside that pre-push hook.

Module-level test functions rather than a class with an interface beside it (ADR-0016),
following tests/meta/test_tools_matrix_covers_every_package.py: pytest collects `test_*`
functions, and the rule is about production code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HOOKS_DIR = ".githooks"
STAGES = ("pre-commit", "commit-msg", "pre-push")
WARNING = "warning: the pre-commit framework's"

# Approves everything the rendered vibey-gh hooks ask of it. Those hooks are not what is
# under test here, only the hand-off they make to the shims, so they must not refuse.
STUB_VIBEY_GH = """#!/bin/sh
case "$1" in
  trailer-key) echo "Made-With" ;;
  trailer) echo "Made-With: the stub in tests/meta" ;;
esac
exit 0
"""

# Stands in for the hook `pre-commit install` generates. It records its stage, whether
# GIT_DIR reached it and its working directory, and for pre-push also the refs that git
# writes on stdin.
FAKE_FRAMEWORK_HOOK = """#!/bin/sh
{{
  printf 'stage=%s git_dir=%s cwd=%s\\n' "{stage}" "${{GIT_DIR-unset}}" "$(pwd -P)"
  if [ "{stage}" = pre-push ]; then sed 's/^/ref: /'; fi
}} >> "{log}"
exit 0
"""

# A framework pre-push hook that does what `vibey.application.conformance` does to make a
# scratch repository: `git init` a directory, then commit to it. With an inherited GIT_DIR
# both land on the repository being pushed instead.
SCRATCH_REPO_HOOK = """#!/bin/sh
cat > /dev/null
git init -q "{scratch}" &&
  git -C "{scratch}" -c user.email=x@example.invalid -c user.name=x \\
    commit --allow-empty -q -m "a scratch repository's first commit"
"""


@dataclass(frozen=True)
class Scratch:
    """A scratch repository: its main checkout, one linked worktree and a bare remote."""

    main: Path
    worktree: Path
    log: Path
    env: dict[str, str]

    def git(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args], cwd=cwd, env=self.env, capture_output=True, text=True, check=False
        )

    def ok(self, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        done = self.git(cwd, *args)
        assert done.returncode == 0, f"git {' '.join(args)}\n{done.stdout}\n{done.stderr}"
        return done

    def framework_hooks(self) -> Path:
        """Where `pre-commit install` writes: the COMMON git dir, whichever checkout asks."""
        common = Path(self.ok(self.main, "rev-parse", "--git-common-dir").stdout.strip())
        return (common if common.is_absolute() else self.main / common) / "hooks"

    def install_framework(self) -> None:
        hooks = self.framework_hooks()
        hooks.mkdir(exist_ok=True)
        for stage in STAGES:
            hook = hooks / stage
            hook.write_text(FAKE_FRAMEWORK_HOOK.format(stage=stage, log=self.log))
            hook.chmod(0o755)

    def commit_and_push(self, cwd: Path, branch: str) -> subprocess.CompletedProcess[str]:
        (cwd / f"{branch}.txt").write_text(f"{branch}\n")
        self.ok(cwd, "add", f"{branch}.txt")
        self.ok(cwd, "commit", "-q", "-m", f"feat: change on {branch}")
        return self.ok(cwd, "push", "-q", "origin", branch)

    def stages_run_in(self, cwd: Path) -> list[str]:
        if not self.log.exists():
            return []
        where = f"cwd={cwd.resolve()}"
        return [
            line.split()[0].removeprefix("stage=")
            for line in self.log.read_text().splitlines()
            if line.startswith("stage=") and line.endswith(where)
        ]


def _scratch_env(bin_dir: Path) -> dict[str, str]:
    scrubbed = ("_VIBEY_GH_SELF", "VIBEY_FRAMEWORK_HOOK_CONFIG")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k not in scrubbed}
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "vibey-gh"
    stub.write_text(STUB_VIBEY_GH)
    stub.chmod(0o755)

    main, worktree, remote = tmp_path / "main", tmp_path / "worktree", tmp_path / "remote.git"
    main.mkdir()
    box = Scratch(main, worktree, tmp_path / "framework.log", _scratch_env(bin_dir))

    box.ok(tmp_path, "init", "-q", "--bare", str(remote))
    box.ok(main, "init", "-q", "-b", "main")
    box.ok(main, "config", "user.name", "tests/meta")
    box.ok(main, "config", "user.email", "meta@example.invalid")
    box.ok(main, "config", "commit.gpgsign", "false")
    box.ok(main, "remote", "add", "origin", str(remote))
    # The tracked hooks exactly as this repository carries them, modes included.
    shutil.copytree(REPO / HOOKS_DIR, main / HOOKS_DIR)
    box.ok(main, "config", "core.hooksPath", HOOKS_DIR)
    box.ok(main, "add", HOOKS_DIR)
    box.ok(main, "commit", "-q", "-m", "chore: carry the hooks")
    box.ok(main, "push", "-q", "origin", "main")
    box.ok(main, "worktree", "add", "-q", str(worktree), "-b", "feature")
    return box


def test_the_scratch_worktree_has_the_layout_that_broke_the_old_shims(scratch: Scratch) -> None:
    """Guards the guard: `.git` must be a file here, or the other tests prove nothing."""
    assert (scratch.worktree / ".git").is_file()
    assert (scratch.main / ".git").is_dir()


@pytest.mark.parametrize("where", ["main", "worktree"])
def test_every_stage_reaches_the_framework(scratch: Scratch, where: str) -> None:
    scratch.install_framework()
    cwd, branch = (scratch.main, "main") if where == "main" else (scratch.worktree, "feature")

    pushed = scratch.commit_and_push(cwd, branch)

    ran = scratch.stages_run_in(cwd)
    assert ran == list(STAGES), f"framework stages run from {where}: {ran}"
    # A plain clone's environment in both layouts: no GIT_DIR for the framework to leak.
    stage_lines = [line for line in scratch.log.read_text().splitlines() if "stage=" in line]
    assert all(" git_dir=unset " in line for line in stage_lines), stage_lines
    # The refs reach the framework intact: pre-commit's pre-push stage reads them from
    # stdin to decide what to check, and with none it runs nothing and says nothing.
    refs = [line for line in scratch.log.read_text().splitlines() if line.startswith("ref: ")]
    assert any(f"refs/heads/{branch}" in line for line in refs), refs
    assert WARNING not in pushed.stderr


def test_a_declared_framework_that_is_not_installed_is_named_not_skipped(
    scratch: Scratch,
) -> None:
    """Nothing installed, but the repository declares the framework: say so, then proceed.

    Proceeding is deliberate. A contributor who has not run `pre-commit install` yet must
    still be able to commit and push, and CI runs the same gates either way.
    """
    (scratch.worktree / ".pre-commit-config.yaml").write_text("repos: []\n")

    (scratch.worktree / "feature.txt").write_text("feature\n")
    scratch.ok(scratch.worktree, "add", "feature.txt")
    committed = scratch.ok(scratch.worktree, "commit", "-q", "-m", "feat: uninstalled")
    pushed = scratch.ok(scratch.worktree, "push", "-q", "origin", "feature")

    for stage, stderr in (
        ("pre-commit", committed.stderr),
        ("commit-msg", committed.stderr),
        ("pre-push", pushed.stderr),
    ):
        assert f"{WARNING} {stage} hook is not installed" in stderr, stderr
    assert not scratch.log.exists()


def test_a_repository_without_the_framework_is_left_alone(scratch: Scratch) -> None:
    pushed = scratch.commit_and_push(scratch.worktree, "feature")

    assert WARNING not in pushed.stderr
    assert not scratch.log.exists()


def test_the_config_that_declares_the_framework_is_a_key(scratch: Scratch) -> None:
    """ADR-0018: which file declares the framework is configurable, defaulting to its own."""
    (scratch.worktree / "elsewhere.yaml").write_text("repos: []\n")
    scratch.env["VIBEY_FRAMEWORK_HOOK_CONFIG"] = "elsewhere.yaml"

    pushed = scratch.commit_and_push(scratch.worktree, "feature")

    assert f"{WARNING} pre-push hook is not installed" in pushed.stderr


def test_the_helper_refuses_to_run_without_a_stage(scratch: Scratch) -> None:
    """An empty stage would make the lookup `<common>/hooks/`, a directory, and exec it."""
    done = subprocess.run(
        ["sh", str(scratch.worktree / HOOKS_DIR / "framework-hook.sh")],
        cwd=scratch.worktree,
        env=scratch.env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2
    assert "usage:" in done.stderr


def test_a_scratch_repository_made_under_the_gate_cannot_touch_the_real_one(
    scratch: Scratch,
) -> None:
    """The damage the first gated push from a worktree actually did, reproduced.

    Without the GIT_DIR hand-off in framework-hook.sh, the `git init` here rewrites the
    shared config to `core.bare = true`, so the main checkout refuses `git status`, and
    the commit lands on the branch being pushed.
    """
    hooks = scratch.framework_hooks()
    hook = hooks / "pre-push"
    hook.write_text(SCRATCH_REPO_HOOK.format(scratch=scratch.log.parent / "made-by-a-test"))
    hook.chmod(0o755)
    (scratch.worktree / "feature.txt").write_text("feature\n")
    scratch.ok(scratch.worktree, "add", "feature.txt")
    scratch.ok(scratch.worktree, "commit", "-q", "-m", "feat: before the push")
    head = scratch.ok(scratch.worktree, "rev-parse", "HEAD").stdout

    scratch.ok(scratch.worktree, "push", "-q", "origin", "feature")

    assert scratch.ok(scratch.main, "config", "--bool", "core.bare").stdout.strip() == "false"
    scratch.ok(scratch.main, "status", "--short")
    assert scratch.ok(scratch.worktree, "rev-parse", "HEAD").stdout == head
    assert (scratch.log.parent / "made-by-a-test" / ".git").is_dir()


def test_an_explicit_git_dir_for_another_repository_is_left_alone(scratch: Scratch) -> None:
    """`git --git-dir=<elsewhere>` is a choice, so only the worktree's own export is dropped."""
    other = scratch.log.parent / "other"
    scratch.ok(scratch.log.parent, "init", "-q", str(other))
    hook = other / ".git" / "hooks" / "pre-push"
    hook.write_text(FAKE_FRAMEWORK_HOOK.format(stage="pre-push", log=scratch.log))
    hook.chmod(0o755)

    done = subprocess.run(
        ["sh", str(scratch.worktree / HOOKS_DIR / "framework-hook.sh"), "pre-push"],
        cwd=scratch.worktree,
        env={**scratch.env, "GIT_DIR": str(other / ".git")},
        input="",
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    assert f" git_dir={other / '.git'} " in scratch.log.read_text()
