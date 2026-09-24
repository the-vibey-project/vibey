# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The rendered pre-push hook applies its scope rule to real pushes, end to end.

A real `git push` to a local bare remote, through the hook `vibey-gh install` renders, with
a `pre-push.local` beside it standing in for the heavy stage (the pre-commit framework in
an adopting repository). Each test says whether that stage ran. A heartbeat -- an empty tree
with no parents on a ref outside refs/heads/ -- pushes without it and without
`--no-verify`; a branch, a tag, a tree with something in it, a commit with a parent, or a
heartbeat riding alongside a branch all run it, with every ref git wrote handed on.

The subprocesses run with every `GIT_*` variable scrubbed and the global and system git
configs ignored, as `test_githooks_in_a_worktree` explains.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from vibey_gh.config import GhConfig
from vibey_gh.install import HOOKS_DIR, TEMPLATES, render_hook
from vibey_gh.push_scope import NO_CODE

TENANT = Path(__file__).resolve().parent.parent
HEARTBEAT = "refs/vibey-gh/sovereign-heartbeat"

# Answers the provenance commands the hook asks for, and hands `push-scope` to the real CLI:
# that command is what is under test.
STUB_VIBEY_GH = f"""#!/bin/sh
case "$1" in
  trailer-key) echo "Made-With"; exit 0 ;;
  trailer) echo "Made-With: the stub in test_push_scope_hook"; exit 0 ;;
  check) exit 0 ;;
  push-scope) PYTHONPATH="{TENANT}" exec "{sys.executable}" -m vibey_gh.cli "$@" ;;
esac
exit 0
"""

LOCAL_HOOK = """#!/bin/sh
{{ echo "heavy stage ran"; sed 's/^/ref: /'; }} >> "{log}"
exit 0
"""


class Repo:
    def __init__(self, tmp_path: Path) -> None:
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        (bin_dir / "vibey-gh").write_text(STUB_VIBEY_GH)
        (bin_dir / "vibey-gh").chmod(0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.pop("_VIBEY_GH_SELF", None)
        self.env["PATH"] = f"{bin_dir}{os.pathsep}{self.env.get('PATH', '')}"
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"
        self.root, self.remote = tmp_path / "work", tmp_path / "remote.git"
        self.log = tmp_path / "heavy.log"
        self.root.mkdir()
        self.git_ok("init", "-q", "--bare", str(self.remote), cwd=tmp_path)
        self.git_ok("init", "-q", "-b", "main")
        self.git_ok("config", "user.name", "test_push_scope_hook")
        self.git_ok("config", "user.email", "scope@example.invalid")
        self.git_ok("config", "commit.gpgsign", "false")
        self.git_ok("remote", "add", "origin", str(self.remote))
        hooks = self.root / HOOKS_DIR
        hooks.mkdir()
        rendered = hooks / "pre-push"
        rendered.write_text(render_hook(TEMPLATES / "pre-push", GhConfig(root=self.root)))
        rendered.chmod(0o755)
        local = hooks / "pre-push.local"
        local.write_text(LOCAL_HOOK.format(log=self.log))
        local.chmod(0o755)
        self.git_ok("config", "core.hooksPath", HOOKS_DIR)
        (self.root / "code.py").write_text("print('code')\n")
        self.git_ok("add", "code.py")
        self.git_ok("commit", "-q", "-m", "feat: code")
        self.empty_tree = self.git_ok("hash-object", "-t", "tree", "-w", "/dev/null")

    def git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def git_ok(self, *args: str, cwd: Path | None = None) -> str:
        done = self.git(*args, cwd=cwd)
        assert done.returncode == 0, f"git {' '.join(args)}\n{done.stdout}\n{done.stderr}"
        return done.stdout.strip()

    def heartbeat(self, *parents: str) -> str:
        flags = [arg for parent in parents for arg in ("-p", parent)]
        return self.git_ok("commit-tree", self.empty_tree, *flags, "-m", "sovereign heartbeat")

    def heavy_stage(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def repo(tmp_path: Path) -> Repo:
    return Repo(tmp_path)


def test_a_heartbeat_pushes_without_the_heavy_stage_and_without_no_verify(repo):
    pushed = repo.git("push", "origin", f"{repo.heartbeat()}:{HEARTBEAT}")
    assert pushed.returncode == 0, pushed.stderr
    assert repo.heavy_stage() == []
    assert "nothing for the pre-push gate to judge" in pushed.stderr
    assert repo.git_ok("ls-remote", "origin", HEARTBEAT, cwd=repo.root)


def test_a_branch_push_runs_the_heavy_stage_with_its_refs(repo):
    assert repo.git("push", "origin", "main").returncode == 0
    lines = repo.heavy_stage()
    assert lines[0] == "heavy stage ran"
    assert any("refs/heads/main" in line for line in lines if line.startswith("ref: "))


@pytest.mark.parametrize(
    "refspec, why",
    [
        (lambda r: f"{r.heartbeat()}:refs/heads/beat", "a branch"),
        (lambda r: f"{r.heartbeat()}:refs/tags/beat", "a tag"),
        (
            lambda r: f"{r.git_ok('commit-tree', 'HEAD^{tree}', '-m', 'x')}:{HEARTBEAT}",
            "a tree with something in it",
        ),
        (lambda r: f"{r.heartbeat(r.heartbeat())}:{HEARTBEAT}", "a commit with a parent"),
        (lambda r: f"HEAD:{HEARTBEAT}", "code on a non-branch ref"),
    ],
)
def test_anything_but_a_heartbeat_runs_the_heavy_stage(repo, refspec, why):
    assert repo.git("push", "origin", refspec(repo)).returncode == 0, why
    assert repo.heavy_stage()[:1] == ["heavy stage ran"], why


def test_a_heartbeat_riding_beside_a_branch_runs_the_heavy_stage_on_both(repo):
    """The pre-commit framework reads only the first ref; the hook reads all of them and
    hands all of them on, so the branch is judged even when the heartbeat comes first."""
    beat = repo.heartbeat()
    assert repo.git("push", "origin", f"{beat}:{HEARTBEAT}", "main").returncode == 0
    refs = [line for line in repo.heavy_stage() if line.startswith("ref: ")]
    assert repo.heavy_stage()[0] == "heavy stage ran"
    assert any(HEARTBEAT in line for line in refs) and any(
        "refs/heads/main" in line for line in refs
    )


def test_a_refusing_heavy_stage_still_refuses_the_push(repo):
    (repo.root / HOOKS_DIR / "pre-push.local").write_text("#!/bin/sh\ncat >/dev/null\nexit 3\n")
    refused = repo.git("push", "origin", "main")
    assert refused.returncode != 0
    assert not repo.git_ok("ls-remote", "origin", "refs/heads/main")


def test_the_hook_and_the_command_agree_on_the_token():
    """The hook compares stdout against a literal; this keeps it the constant the command
    prints, so neither can change alone."""
    assert f'"$scope" = "{NO_CODE}"' in (TEMPLATES / "pre-push").read_text(encoding="utf-8")
