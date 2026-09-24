# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The repository the heartbeat timer owns: created and repaired from the tree, checked, and
its gate asked about a synthetic heartbeat exactly as a push would ask it.

Every clone here is a real git repository under pytest's `tmp_path`, with git's global and
system configuration replaced -- never the repository the suite runs in.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

from vibey_gh.heartbeat_clone import GATE_PASSED, HOOK_TEMPLATE, HeartbeatClone
from vibey_gh.interfaces.heartbeat_clone_interface import HeartbeatCloneInterface
from vibey_gh.sovereign_runner import TEMPLATES

REF = "refs/vibey-gh/sovereign-heartbeat"
REMOTE = "https://github.com/o/r"


@pytest.fixture(autouse=True)
def _hermetic_git(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith("GIT_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _clone(tmp_path: Path, **seams) -> HeartbeatClone:
    return HeartbeatClone(
        tmp_path / "heartbeat-r",
        remote_url=REMOTE,
        gh_config_dir=tmp_path / "gh runner",
        heartbeat_ref=REF,
        path_env=os.environ["PATH"],
        **seams,
    )


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout.strip()


def _hook(clone: HeartbeatClone, python: str) -> None:
    text = (TEMPLATES / HOOK_TEMPLATE).read_text(encoding="utf-8")
    clone.hook_path.write_text(text.replace("__PYTHON__", shlex.quote(python)), encoding="utf-8")
    clone.hook_path.chmod(0o755)


def test_the_clone_honours_its_interface(tmp_path):
    assert isinstance(_clone(tmp_path), HeartbeatCloneInterface)


def test_its_settings_are_its_remote_its_gate_and_the_runners_own_credential(tmp_path):
    clone = _clone(tmp_path)
    settings = clone.settings()
    assert settings["remote.origin.url"] == (REMOTE,)
    assert settings["core.hooksPath"] == (str(tmp_path / "heartbeat-r/.git/hooks"),)
    reset, helper = settings["credential.helper"]
    assert reset == ""
    assert helper.startswith("!env -u GH_TOKEN -u GITHUB_TOKEN -u GH_ENTERPRISE_TOKEN")
    assert f"GH_CONFIG_DIR={shlex.quote(str(tmp_path / 'gh runner'))}" in helper
    assert helper.endswith(" gh auth git-credential")
    assert clone.hook_path == tmp_path / "heartbeat-r/.git/hooks/pre-push"
    assert clone.config_path == tmp_path / "heartbeat-r/.vibey-gh.toml"


def test_ensure_creates_the_clone_with_no_working_tree_to_speak_of(tmp_path):
    clone = _clone(tmp_path)
    lines, problem = clone.ensure()
    assert problem == ""
    assert lines[0] == f"created the heartbeat's clone at {clone.path}"
    assert (clone.path / ".git").is_dir()
    assert _git(clone.path, "ls-files") == ""
    assert clone.problems() == []
    held = _git(clone.path, "config", "--local", "--get-all", "-z", "credential.helper")
    assert held.split("\0")[:-1] == ["", clone.settings()["credential.helper"][1]]


def test_ensure_repairs_only_what_drifted(tmp_path):
    clone = _clone(tmp_path)
    clone.ensure()
    _git(clone.path, "config", "--local", "remote.origin.url", "https://example.invalid/fork")
    _git(clone.path, "config", "--local", "--unset-all", "credential.helper")
    assert clone.problems() == [
        (
            f"drift: remote.origin.url in {clone.path} is ['https://example.invalid/fork'],"
            f" not ['{REMOTE}']"
        ),
        (
            f"drift: credential.helper in {clone.path} is [], not"
            f" {list(clone.settings()['credential.helper'])}"
        ),
    ]
    lines, problem = clone.ensure()
    assert problem == "" and lines == [
        f"set remote.origin.url in {clone.path}",
        f"set credential.helper in {clone.path}",
    ]
    assert clone.problems() == []
    assert clone.ensure() == ([], "")


def test_a_missing_clone_is_named(tmp_path):
    clone = _clone(tmp_path)
    assert clone.problems() == [
        f"missing: the heartbeat's clone {clone.path} (vibey-gh heartbeat install creates it)"
    ]


def test_a_setting_git_refuses_stops_the_repair(tmp_path):
    clone = _clone(tmp_path)
    clone.ensure()

    def git(args, cwd):
        if args[:3] == ("config", "--local", "--add"):
            return 255, ""
        return HeartbeatClone._run_git(args, cwd)

    _git(clone.path, "config", "--local", "--unset-all", "core.hooksPath")
    broken = _clone(tmp_path, git=git)
    lines, problem = broken.ensure()
    assert lines == []
    assert problem == f"could not set core.hooksPath in {clone.path} (git config exited 255)"


def test_the_credential_helper_is_the_only_one_git_uses(tmp_path, monkeypatch):
    """The empty value resets every helper an inherited configuration names -- a generic one
    and a URL-scoped one both -- and the one left runs gh with the runner's own login and
    every ambient token stripped. Shown with a real `git credential fill` and a stand-in gh."""
    log = tmp_path / "helpers.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "gh").write_text(
        "#!/bin/sh\ncat >/dev/null\n"
        f'echo "gh $* dir=$GH_CONFIG_DIR token=${{GH_TOKEN-unset}}" >> "{log}"\n'
        "echo username=runner\necho password=from-the-runners-login\n",
        encoding="utf-8",
    )
    (fake_bin / "gh").chmod(0o755)
    inherited = tmp_path / "inherited.gitconfig"
    inherited.write_text(
        '[credential "https://github.com"]\n'
        f'\thelper = "!f() {{ echo url-scoped >> {log}; echo password=operators; }}; f"\n'
        "[credential]\n"
        f'\thelper = "!f() {{ echo generic >> {log}; }}; f"\n',
        encoding="utf-8",
    )
    clone = _clone(tmp_path)
    clone.ensure()
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(inherited))
    monkeypatch.setenv("GH_TOKEN", "an-ambient-token")
    monkeypatch.setenv("PATH", f"{fake_bin}{os.pathsep}{os.environ['PATH']}")
    filled = subprocess.run(
        ["git", "credential", "fill"],
        cwd=clone.path,
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "password=from-the-runners-login" in filled
    assert log.read_text(encoding="utf-8").splitlines() == [
        f"gh auth git-credential get dir={tmp_path / 'gh runner'} token=unset"
    ]


# --- the gate check ---------------------------------------------------------------------------


def test_the_real_gate_lets_a_synthetic_heartbeat_through(tmp_path):
    """The hook exactly as installed, the real vibey_gh behind it: its own scope decision
    prints the token, and the check says nothing is wrong."""
    clone = _clone(tmp_path)
    clone.ensure()
    _hook(clone, sys.executable)
    assert clone.gate_check() == ""


def test_the_real_gate_refuses_when_its_interpreter_cannot_decide(tmp_path):
    """An interpreter with no `push-scope` -- a tool install older than the rule -- is a
    gate that refuses every push, and the check says so, with what the hook said."""
    clone = _clone(tmp_path)
    clone.ensure()
    old = tmp_path / "old-python"
    old.write_text(
        "#!/bin/sh\necho \"vibey-gh: error: argument cmd: invalid choice: 'push-scope'\" >&2\n"
        "exit 2\n",
        encoding="utf-8",
    )
    old.chmod(0o755)
    _hook(clone, str(old))
    problem = clone.gate_check()
    assert problem.startswith(
        "the clone's own pre-push gate did not let a synthetic heartbeat through (exit 1): "
    )
    assert "invalid choice: 'push-scope'" in problem
    assert "✖ push refused: this repository publishes only the sovereign heartbeat." in problem
    assert "\x1b[" not in problem
    assert "uv tool install --force --from . vibey" in problem


def test_a_gate_that_exits_zero_without_the_token_is_not_a_pass(tmp_path):
    clone = _clone(tmp_path, hook=lambda argv, cwd, stdin, env: (0, "all good, trust me\n"))
    clone.ensure()
    problem = clone.gate_check()
    assert "(exit 0): all good, trust me;" in problem


def test_a_gate_that_says_nothing_is_reported_as_such(tmp_path):
    clone = _clone(tmp_path, hook=lambda argv, cwd, stdin, env: (126, ""))
    clone.ensure()
    assert clone.gate_check().startswith(
        "the clone's own pre-push gate did not let a synthetic heartbeat through (exit 126); "
    )


def test_the_gate_is_handed_exactly_what_a_push_would_hand_it(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/somewhere/else")
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-the-clone"))
    handed = []

    def hook(argv, cwd, stdin, env):
        handed.append((tuple(argv), cwd, stdin, dict(env)))
        return 0, f"{GATE_PASSED}\n"

    clone = _clone(tmp_path, hook=hook)
    monkeypatch.delenv("GIT_DIR")
    clone.ensure()
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "not-the-clone"))
    assert clone.gate_check() == ""
    monkeypatch.delenv("GIT_DIR")
    ((argv, cwd, stdin, env),) = handed
    assert argv == (str(clone.hook_path), "origin", REMOTE) and cwd == clone.path
    local, sha, ref, old = stdin.split()
    assert local == sha and ref == REF and set(old) == {"0"} and len(old) == len(sha)
    assert _git(clone.path, "cat-file", "-t", sha) == "commit"
    assert "PYTHONPATH" not in env and "GIT_DIR" not in env
    assert env["PATH"] == os.environ["PATH"]


@pytest.mark.parametrize(
    "failing, expected",
    [
        ("hash-object", "could not compute the empty tree"),
        ("commit-tree", "could not make a synthetic heartbeat"),
    ],
)
def test_a_clone_that_cannot_make_a_heartbeat_says_so(tmp_path, failing, expected):
    def git(args, cwd):
        if failing in args:
            return 128, ""
        return HeartbeatClone._run_git(args, cwd)

    clone = _clone(tmp_path, git=git)
    clone.ensure()
    assert clone.gate_check() == f"{expected} in {clone.path}"


# --- the default seams ------------------------------------------------------------------------


def test_the_default_git_seam_addresses_the_clone_and_nothing_else(tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    subprocess.run(["git", "init", "-q", str(elsewhere)], check=True)
    clone = _clone(tmp_path)
    clone.ensure()
    monkeypatch.setenv("GIT_DIR", str(elsewhere / ".git"))
    assert HeartbeatClone._run_git(("rev-parse", "--absolute-git-dir"), clone.path) == (
        0,
        str(Path(os.path.realpath(clone.path / ".git"))),
    )
    monkeypatch.setenv("PATH", str(tmp_path / "no-git-here"))
    assert HeartbeatClone._run_git(("status",), clone.path) == (127, "")


def test_the_default_hook_seam_runs_the_hook_without_a_shell(tmp_path):
    hook = tmp_path / "hook"
    hook.write_text('#!/bin/sh\nread line\necho "got $line $1"\necho err >&2\n', encoding="utf-8")
    hook.chmod(0o755)
    code, said = HeartbeatClone._run_hook(
        (str(hook), "origin"), tmp_path, "a b c d\n", dict(os.environ)
    )
    assert code == 0 and said == "got a b c d origin\nerr\n"
    code, said = HeartbeatClone._run_hook(
        (str(tmp_path / "absent"),), tmp_path, "", dict(os.environ)
    )
    assert code == 127 and said
