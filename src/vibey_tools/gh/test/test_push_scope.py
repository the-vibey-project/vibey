# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pre-push gate recognises, by its own rule, a push that carries no code.

The rule, and every way around it that must NOT work: a push passes the gate without the
heavy stage only when EVERY ref it updates is the declared heartbeat ref and EVERY commit it
sends is an empty tree with no parents that brings nothing else along. A branch, a tag, any
other ref, a tree with anything in it, a commit with a parent, a deletion, an annotated tag
object, a replacement standing in for the object the push sends, a graft handing the pack a
parent, a line git never writes, an unreadable object, or no refs at all -- each of those
runs the full gate.

These run against real git objects in a scratch repository under pytest's `tmp_path`, never
a table of canned answers and never the repository the suite runs in: the rule is about what
git holds, so git is what answers, and a replacement or a graft changes history for every
worktree that shares the repository it is written into.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from vibey_gh.cli import main
from vibey_gh.interfaces.push_scope_interface import PushScopeInterface, PushVerdictInterface
from vibey_gh.push_scope import NO_CODE, NO_REPLACE_OBJECTS, PushScope, PushVerdict

ZERO = "0" * 40
HEARTBEAT = "refs/vibey-gh/sovereign-heartbeat"


def _env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _git(cwd: Path, *args: str, stdin: str | None = None) -> str:
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=_env(),
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, f"git {' '.join(args)}\n{done.stderr}"
    return done.stdout.strip()


class Objects:
    """A scratch repository and the handful of objects the rule is about."""

    def __init__(self, root: Path) -> None:
        self.root = root
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.name", "test_push_scope")
        _git(root, "config", "user.email", "scope@example.invalid")
        _git(root, "config", "commit.gpgsign", "false")
        self.empty_tree = _git(root, "hash-object", "-t", "tree", "-w", "/dev/null")
        self.heartbeat = _git(root, "commit-tree", self.empty_tree, "-m", "sovereign heartbeat")
        (root / "code.py").write_text("print('code')\n", encoding="utf-8")
        _git(root, "add", "code.py")
        _git(root, "commit", "-q", "-m", "feat: code")
        self.code = _git(root, "rev-parse", "HEAD")
        self.full_tree = _git(root, "rev-parse", "HEAD^{tree}")
        # A root commit that carries a tree: no parents, but not empty.
        self.rooted_code = _git(root, "commit-tree", self.full_tree, "-m", "root with code")
        # An empty tree that nonetheless has a parent: it carries history.
        self.parented_empty = _git(
            root, "commit-tree", self.empty_tree, "-p", self.heartbeat, "-m", "has a parent"
        )
        _git(root, "tag", "-a", "v1", "-m", "annotated", self.heartbeat)
        self.tag_object = _git(root, "rev-parse", "refs/tags/v1")

    def git_dir(self) -> Path:
        return self.root / _git(self.root, "rev-parse", "--git-dir")


@pytest.fixture
def objects(tmp_path: Path) -> Objects:
    return Objects(tmp_path)


def _line(sha: str, remote_ref: str, *, local: str | None = None, old: str = ZERO) -> str:
    return f"{local or sha} {sha} {remote_ref} {old}"


def _scope(objects: Objects, *refs: str) -> PushScope:
    return PushScope(refs=refs or (HEARTBEAT,), cwd=objects.root)


def _judge(objects: Objects, *lines: str) -> PushVerdict:
    return _scope(objects).judge("\n".join(lines) + "\n")


def test_the_scope_check_and_its_verdict_honour_their_interfaces(objects):
    scope = _scope(objects)
    assert isinstance(scope, PushScopeInterface)
    assert isinstance(scope.judge(""), PushVerdictInterface)


def test_a_heartbeat_push_carries_no_code(objects):
    verdict = _judge(objects, _line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is False
    assert HEARTBEAT in verdict.reason and "no code" in verdict.reason
    assert "the declared heartbeat" in verdict.reason


def test_replacing_an_earlier_heartbeat_still_carries_no_code(objects):
    """The remote's old value is what the push replaces, not what it sends; it is never
    read, so an old value the local repository lacks cannot make the verdict unreadable."""
    verdict = _judge(objects, _line(objects.heartbeat, HEARTBEAT, old="f" * 40))
    assert verdict.carries_code is False


def test_only_the_declared_refs_are_ever_exempt(objects):
    """12.c: the exemption is exactly as wide as the declaration. A ref outside
    refs/heads/ and refs/tags/ that nobody declared is judged in full, heartbeat or not;
    two declared refs in one push are both exempt."""
    pulse = "refs/vibey/pulse"
    verdict = _judge(objects, _line(objects.heartbeat, pulse))
    assert verdict.carries_code is True
    assert f"{pulse} is not the declared heartbeat ref ({HEARTBEAT})" in verdict.reason
    both = _scope(objects, HEARTBEAT, pulse).judge(
        f"{_line(objects.heartbeat, HEARTBEAT)}\n{_line(objects.heartbeat, pulse)}\n"
    )
    assert both.carries_code is False and HEARTBEAT in both.reason and pulse in both.reason


def test_nothing_is_exempt_when_nothing_is_declared(objects):
    verdict = PushScope(cwd=objects.root).judge(_line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is True and "none is declared" in verdict.reason


@pytest.mark.parametrize(
    "build, expected",
    [
        # A branch, even with an empty parentless commit on it.
        (lambda o: [_line(o.heartbeat, "refs/heads/main")], "refs/heads/main is a branch"),
        # A tag, lightweight or annotated.
        (lambda o: [_line(o.heartbeat, "refs/tags/v2")], "refs/tags/v2 is a tag"),
        (lambda o: [_line(o.tag_object, HEARTBEAT)], "is not a commit"),
        # A tree with something in it, on the declared ref.
        (lambda o: [_line(o.rooted_code, HEARTBEAT)], "carries a tree"),
        (lambda o: [_line(o.code, HEARTBEAT)], "carries a tree"),
        # A commit with a parent, even with an empty tree.
        (lambda o: [_line(o.parented_empty, HEARTBEAT)], "has a parent"),
        # A deletion sends nothing to judge, and is still not a heartbeat.
        (lambda o: [f"(delete) {ZERO} {HEARTBEAT} {o.heartbeat}"], "deletes"),
        # An object the repository does not hold.
        (lambda o: [_line("e" * 40, HEARTBEAT)], "could not read"),
        # A name git would never write on this stdin.
        (lambda o: [_line(o.heartbeat, "HEAD")], "is not a full ref name"),
        (lambda o: [_line("not-a-sha", HEARTBEAT)], "is not an object name"),
        (lambda o: ["only three fields"], "is not a pre-push line"),
    ],
)
def test_every_push_that_is_not_purely_heartbeats_runs_the_full_gate(objects, build, expected):
    verdict = _judge(objects, *build(objects))
    assert verdict.carries_code is True
    assert expected in verdict.reason


def test_a_heartbeat_cannot_carry_a_branch_past_the_gate(objects):
    """The bypass a per-hook check would have missed. The pre-commit framework reads only
    the FIRST ref git hands it, so a push whose first ref is a heartbeat and whose second is
    a branch would look like a heartbeat to anything reading the framework's variables. The
    scope check reads every line, and one branch anywhere runs the whole gate."""
    for lines in (
        [_line(objects.heartbeat, HEARTBEAT), _line(objects.code, "refs/heads/main")],
        [_line(objects.code, "refs/heads/main"), _line(objects.heartbeat, HEARTBEAT)],
        [_line(objects.heartbeat, HEARTBEAT), _line(objects.heartbeat, "refs/tags/v9")],
    ):
        verdict = _judge(objects, *lines)
        assert verdict.carries_code is True, lines


@pytest.mark.parametrize("stdin", ["", "\n", "   \n\n"])
def test_no_refs_at_all_is_not_proof_of_no_code(objects, stdin):
    verdict = _scope(objects).judge(stdin)
    assert verdict.carries_code is True and "no refs" in verdict.reason


# --- judged as the push sends it: replacements ignored, the whole object set walked --------


def test_a_replacement_cannot_dress_code_as_a_heartbeat(objects):
    """`git replace <code> <heartbeat>` makes every reading command describe the empty root
    when asked about the code commit, while the pack sends the code commit itself
    (git-replace(1): pack transfer does not follow replacements). Read without
    replacements, the code is what is judged."""
    _git(objects.root, "replace", objects.code, objects.heartbeat)
    assert _git(objects.root, "cat-file", "commit", objects.code).startswith(
        f"tree {objects.empty_tree}"
    ), "the replacement is in force for an ordinary read"
    verdict = _judge(objects, _line(objects.code, HEARTBEAT))
    assert verdict.carries_code is True and "carries a tree" in verdict.reason
    assert objects.code in verdict.reason


def test_a_heartbeat_replaced_by_code_is_still_judged_as_the_heartbeat_it_sends(objects):
    """The other direction: the object sent is the empty root, whatever a replacement says,
    so it carries no code -- the verdict follows the push, not the display."""
    _git(objects.root, "replace", objects.heartbeat, objects.code)
    verdict = _judge(objects, _line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is False, verdict.reason


def test_a_graft_that_would_hand_the_pack_a_parent_runs_the_full_gate(objects):
    """A graft gives the empty root a parent its own bytes never name. The raw commit
    still reads as parentless with an empty tree, but the pack walks the graft and would
    carry the parent's code; so does `rev-list --objects`, which is what is judged."""
    grafts = objects.git_dir() / "info" / "grafts"
    grafts.parent.mkdir(parents=True, exist_ok=True)
    grafts.write_text(f"{objects.heartbeat} {objects.code}\n", encoding="utf-8")
    raw = _git(objects.root, "cat-file", "commit", objects.heartbeat)
    assert "parent " not in raw, "the graft does not change the commit's own bytes"
    verdict = _judge(objects, _line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is True
    assert "would carry" in verdict.reason and "graft" in verdict.reason
    ok, why = _scope(objects).is_empty_root(objects.heartbeat)
    assert not ok and "would carry" in why


def test_every_git_argv_the_scope_builds_refuses_replacements(objects):
    """In the argv itself, not only in the default runner: an injected runner -- the
    heartbeat's own lease check is one -- is handed the same refusal."""
    asked: list[tuple[str, ...]] = []
    real = _scope(objects)

    def git(args):
        asked.append(tuple(args))
        return real._git(args)

    PushScope(refs=(HEARTBEAT,), git=git).judge(_line(objects.heartbeat, HEARTBEAT))
    assert asked and all(argv[0] == NO_REPLACE_OBJECTS for argv in asked)
    subcommands = {argv[1] for argv in asked}
    assert {"hash-object", "cat-file", "rev-list"} <= subcommands


def test_the_empty_tree_is_asked_of_git_not_compiled_in(objects):
    """The empty tree's id depends on the repository's object format (SHA-1 or SHA-256),
    so it is computed by the repository, never written down."""
    asked: list[tuple[str, ...]] = []
    real = _scope(objects)

    def git(args):
        asked.append(tuple(args))
        return real._git(args)

    PushScope(refs=(HEARTBEAT,), git=git).judge(_line(objects.heartbeat, HEARTBEAT))
    assert (NO_REPLACE_OBJECTS, "hash-object", "-t", "tree", "/dev/null") in asked


def test_a_git_that_cannot_answer_runs_the_full_gate(objects):
    scope = PushScope(refs=(HEARTBEAT,), git=lambda args: (1, ""))
    verdict = scope.judge(_line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is True and "empty tree" in verdict.reason
    assert scope.is_empty_root(objects.heartbeat) == (
        False,
        "git could not compute the empty tree to compare against",
    )


def test_an_object_git_names_but_cannot_print_runs_the_full_gate(objects):
    real = _scope(objects)

    def git(args):
        return (128, "") if args[1:3] == ("cat-file", "commit") else real._git(args)

    verdict = PushScope(refs=(HEARTBEAT,), git=git).judge(_line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is True and "could not read" in verdict.reason


def test_an_object_set_git_cannot_list_runs_the_full_gate(objects):
    real = _scope(objects)

    def git(args):
        return (128, "") if args[1] == "rev-list" else real._git(args)

    verdict = PushScope(refs=(HEARTBEAT,), git=git).judge(_line(objects.heartbeat, HEARTBEAT))
    assert verdict.carries_code is True and "could not list the objects" in verdict.reason


def test_a_missing_git_is_an_answer_of_its_own(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", str(tmp_path))
    assert PushScope(cwd=tmp_path)._git(("status",))[0] != 0


def test_is_empty_root_says_why_a_commit_is_not_a_heartbeat(objects):
    scope = _scope(objects)
    assert scope.is_empty_root(objects.heartbeat) == (True, "")
    ok, why = scope.is_empty_root(objects.parented_empty)
    assert not ok and "has a parent" in why
    ok, why = scope.is_empty_root(objects.code)
    assert not ok and "carries a tree" in why


# --- the command the hook runs ---------------------------------------------------------------


def test_the_command_prints_the_token_only_when_there_is_nothing_to_judge(
    objects, monkeypatch, capsys
):
    """The hook skips the heavy stage only on the exact token on stdout AND a zero exit.
    Anything else -- an older vibey-gh without this command, a crash, a stub that exits 0
    for everything -- prints no token, and the full gate runs. The declared ref is the
    configuration's own default here, `[pr_automation.fallback] heartbeat_ref`."""
    monkeypatch.chdir(objects.root)
    monkeypatch.setattr("sys.stdin", _Stdin(_line(objects.heartbeat, HEARTBEAT) + "\n"))
    assert main(["push-scope"]) == 0
    out, err = capsys.readouterr()
    assert out.strip() == NO_CODE
    assert "nothing for the pre-push gate to judge" in err

    monkeypatch.setattr("sys.stdin", _Stdin(_line(objects.code, "refs/heads/main") + "\n"))
    assert main(["push-scope"]) == 1
    out, err = capsys.readouterr()
    assert out == "" and err == ""


def test_the_command_exempts_the_ref_the_configuration_declares(objects, monkeypatch, capsys):
    (objects.root / ".vibey-gh.toml").write_text(
        '[pr_automation.fallback]\nheartbeat_ref = "refs/vibey/pulse"\n', encoding="utf-8"
    )
    monkeypatch.chdir(objects.root)
    monkeypatch.setattr("sys.stdin", _Stdin(_line(objects.heartbeat, HEARTBEAT) + "\n"))
    assert main(["push-scope"]) == 1
    assert capsys.readouterr().out == ""
    monkeypatch.setattr("sys.stdin", _Stdin(_line(objects.heartbeat, "refs/vibey/pulse") + "\n"))
    assert main(["push-scope"]) == 0
    assert capsys.readouterr().out.strip() == NO_CODE


def test_a_configuration_that_cannot_be_read_exempts_nothing(objects, monkeypatch, capsys):
    (objects.root / ".vibey-gh.toml").write_text("[pr_automation.fallback\n", encoding="utf-8")
    monkeypatch.chdir(objects.root)
    monkeypatch.setattr("sys.stdin", _Stdin(_line(objects.heartbeat, HEARTBEAT) + "\n"))
    assert main(["push-scope"]) == 1
    out, err = capsys.readouterr()
    assert out == "" and "no heartbeat ref could be read" in err


class _Stdin:
    def __init__(self, text: str) -> None:
        self._text = text

    def read(self) -> str:
        return self._text
