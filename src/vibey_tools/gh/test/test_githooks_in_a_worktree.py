# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The installed hooks keep their chain intact when git runs them from a linked worktree.

`install` moves a repository's own hook aside to `<hook>.local`, and the rendered hook
chains to it. Adopters use that chain to reach the pre-commit framework, which is where
their gate suite lives. In the vibey monorepo the `.local` shims found the framework by
the literal `.git/hooks/<stage>`. In a linked worktree `.git` is a FILE, so that path
never exists, and every push from a worktree ran no gate at all and said nothing
(vibey #282).

That defect was in the repository's own shims, not in these templates. The templates
find their sibling through `$(dirname "$0")`, and that works in both layouts. This
module pins it: the rendered hooks run through a real `git commit` and `git push` from
a main checkout and from a linked worktree, and each one must reach its `.local`.

The subprocesses run with every `GIT_*` variable scrubbed and the global and system git
configs ignored. A git hook exports `GIT_DIR`, and a scratch `git commit` that inherited
it would commit to whatever repository ran this suite.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vibey_gh.config import GhConfig
from vibey_gh.install import HOOKS, HOOKS_DIR, TEMPLATES, render_hook

STUB_VIBEY_GH = """#!/bin/sh
case "$1" in
  trailer-key) echo "Made-With" ;;
  trailer) echo "Made-With: the stub in test_githooks_in_a_worktree" ;;
esac
exit 0
"""

# The adopter's own hook, moved aside by `install`. It records which hook chained to it,
# where it ran, and for pre-push the refs git wrote on stdin.
LOCAL_HOOK = """#!/bin/sh
{{
  printf 'hook=%s cwd=%s\\n' "{hook}" "$(pwd -P)"
  if [ "{hook}" = pre-push ]; then sed 's/^/ref: /'; fi
}} >> "{log}"
exit 0
"""


def _env(bin_dir: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.pop("_VIBEY_GH_SELF", None)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _git(cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=env, capture_output=True, text=True, check=False
    )
    command = " ".join(args)
    assert done.returncode == 0, f"git {command}\n{done.stdout}\n{done.stderr}"
    return done


@pytest.fixture
def layout(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    """A main checkout, a linked worktree of it, and a bare remote they both push to."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "vibey-gh").write_text(STUB_VIBEY_GH)
    (bin_dir / "vibey-gh").chmod(0o755)
    env = _env(bin_dir)

    main, worktree, remote = tmp_path / "main", tmp_path / "worktree", tmp_path / "remote.git"
    log = tmp_path / "local-hooks.log"
    main.mkdir()
    _git(tmp_path, env, "init", "-q", "--bare", str(remote))
    _git(main, env, "init", "-q", "-b", "main")
    _git(main, env, "config", "user.name", "test_githooks_in_a_worktree")
    _git(main, env, "config", "user.email", "hooks@example.invalid")
    _git(main, env, "config", "commit.gpgsign", "false")
    _git(main, env, "remote", "add", "origin", str(remote))

    hooks = main / HOOKS_DIR
    hooks.mkdir()
    cfg = GhConfig(root=main)
    for hook in HOOKS:
        rendered = hooks / hook
        rendered.write_text(render_hook(TEMPLATES / hook, cfg), encoding="utf-8")
        rendered.chmod(0o755)
        local = hooks / f"{hook}.local"
        local.write_text(LOCAL_HOOK.format(hook=hook, log=log))
        local.chmod(0o755)
    _git(main, env, "config", "core.hooksPath", HOOKS_DIR)
    _git(main, env, "add", HOOKS_DIR)
    _git(main, env, "commit", "-q", "-m", "chore: carry the hooks")
    _git(main, env, "push", "-q", "origin", "main")
    _git(main, env, "worktree", "add", "-q", str(worktree), "-b", "feature")
    log.unlink()
    return main, worktree, log, env


@pytest.mark.parametrize("where", ["main", "worktree"])
def test_each_rendered_hook_reaches_its_local_sibling(layout, where):
    main, worktree, log, env = layout
    cwd, branch = (main, "main") if where == "main" else (worktree, "feature")
    assert (cwd / ".git").is_file() is (where == "worktree")

    (cwd / "change.txt").write_text(f"{branch}\n")
    _git(cwd, env, "add", "change.txt")
    _git(cwd, env, "commit", "-q", "-m", f"feat: change on {branch}")
    _git(cwd, env, "push", "-q", "origin", branch)

    lines = log.read_text().splitlines()
    ran = [line.split()[0].removeprefix("hook=") for line in lines if line.startswith("hook=")]
    assert ran == ["commit-msg", "pre-push"], lines
    here = f"cwd={cwd.resolve()}"
    assert all(line.endswith(here) for line in lines if line.startswith("hook=")), lines
    # pre-push's refs survive the chain: the framework reads them from stdin, and with
    # none it decides there is nothing to check and runs no gate at all.
    assert any(line.startswith("ref: ") and f"refs/heads/{branch}" in line for line in lines)
    # And the rendered commit-msg still did its own job after chaining.
    message = _git(cwd, env, "log", "-1", "--format=%B").stdout
    assert "Made-With: the stub in test_githooks_in_a_worktree" in message


@pytest.mark.parametrize("hook", HOOKS)
def test_a_rendered_hook_never_spells_a_path_inside_dot_git(hook):
    """`.git` is a directory only in a plain clone; in a linked worktree it is a file."""
    text = render_hook(TEMPLATES / hook, GhConfig(root=Path(".")))
    assert ".git/" not in text
    assert f'"$(dirname "$0")/{hook}.local"' in text
