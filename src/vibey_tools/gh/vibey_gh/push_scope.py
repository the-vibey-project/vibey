# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pre-push gate's scope: a push that carries no code has nothing for it to judge.

The pre-push stage exists to judge code on its way off the machine: type-check it, test it,
audit what it depends on. Some pushes carry none. The sovereign heartbeat (doctrine 8.a) is
an empty tree with no parents, pushed to `[pr_automation.fallback] heartbeat_ref`: no diff,
no file, no dependency. Running the full suite over it is not diligence, it is a timer that
cannot finish inside its own interval -- measured at more than two minutes against 1.2
seconds.

The old answer was for the CALLER to skip the gate with `git push --no-verify`. That is a
means whose purpose is to make a check stop applying, which sub-doctrine 12.d forbids with no
exceptions, and it skips the gate for whatever the push happens to carry. This is the other
answer: the gate applies its own rule to what git hands it, and that rule is narrow enough to
state in one sentence. A push carries no code only when **every** ref it updates is the
declared heartbeat ref, and **every** commit it sends is the empty tree with no parents and
brings no other object with it.

Four properties make it safe to trust:

- **It reads git's own list, all of it.** The refs come from the pre-push hook's standard
  input, which git writes and which is the only place the list is complete: the pre-commit
  framework reads only the first line (`_pre_push_ns` in pre-commit 4.6.2) and exports only
  that ref, so a check reading the framework's variables would pass a push whose first ref is
  a heartbeat and whose second is a branch.
- **It asks git about the objects the push will send**, never the caller. Every read is made
  with `--no-replace-objects`, because git follows `refs/replace/*` when it reads an object
  and pack transfer does not: with a replacement in place, `cat-file` would describe the
  replacement while the push sent the original. And the whole object set is judged, not only
  the commit: `rev-list --objects` must name exactly the commit and the empty tree. That is
  the traversal the pack itself makes, so a graft (`info/grafts`, or `GIT_GRAFT_FILE`) that
  would hand the pack a parent's code is seen here too. The empty tree's id is computed by
  the repository, so a SHA-256 repository is judged in its own format.
- **It exempts one ref, the declared one** (12.c). A ref that merely sits outside
  `refs/heads/` and `refs/tags/` is not enough: only `[pr_automation.fallback]
  heartbeat_ref` is ever exempt, so the rule is exactly as wide as the one thing it was
  written for.
- **It fails closed.** A branch, a tag, any other ref, a tree with anything in it, a commit
  with a parent, an object the commit brings along, a deletion, an object that is not a
  commit, a line git would never write, an object git cannot read, no refs at all -- every
  one carries code, and the full gate runs.

The hook skips its heavy stage only on the exact `NO_CODE` token on standard output, so a
`vibey-gh` too old to know this command, or one that crashes, runs the full gate.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Collection, Sequence
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.interfaces.push_scope_interface import PushScopeInterface

__all__ = ["NO_CODE", "NO_REPLACE_OBJECTS", "PushScope", "PushVerdict"]

# What `vibey-gh push-scope` prints, and all it prints, when a push carries no code. The hook
# compares standard output against it exactly; nothing else skips the heavy stage.
NO_CODE = "carries-no-code"

# The first word of every git argv this module builds -- in the argv itself, not only in the
# default runner, so an injected runner is handed it too. git follows `refs/replace/*` when
# it reads an object, and pack transfer does not (git-replace(1)), so without it a
# replacement would be judged in place of the object the push actually sends.
NO_REPLACE_OBJECTS = "--no-replace-objects"

_OBJECT_NAME = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

GitRunner = Callable[[Sequence[str]], tuple[int, str]]


@dataclass(frozen=True)
class PushVerdict:
    """Whether a push carries code, and why. Satisfies `PushVerdictInterface` by shape:
    a frozen dataclass cannot inherit the protocol's read-only properties."""

    carries_code: bool
    reason: str


class PushScope(PushScopeInterface):
    """Judges git's pre-push input by the gate's own rule; see the module docstring.

    `refs` are the only refs a push that carries no code may update: the declared heartbeat
    ref, as `vibey-gh push-scope` reads it from `[pr_automation.fallback]`. With none, no
    push is ever exempt. `git` is the seam: it takes the arguments after `git` and returns
    the exit status and the stripped standard output. The default runs git in `cwd`, which
    inside a hook is the top of the working tree git is pushing from.
    """

    def __init__(
        self,
        *,
        refs: Collection[str] = (),
        git: GitRunner | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        self._refs = frozenset(refs)
        self._cwd = cwd
        self._run = git or self._git

    def judge(self, pre_push_input: str) -> PushVerdict:
        lines = [line for line in pre_push_input.splitlines() if line.strip()]
        if not lines:
            return PushVerdict(True, "no refs were given, which proves nothing about the push")
        empty_tree = self._empty_tree()
        if not empty_tree:
            return PushVerdict(True, "git could not compute the empty tree to compare against")
        refs = []
        for line in lines:
            problem = self._line_problem(line, empty_tree)
            if problem:
                return PushVerdict(True, problem)
            refs.append(line.rsplit(maxsplit=3)[2])
        return PushVerdict(
            False,
            f"this push carries no code: it updates only {', '.join(refs)}, the declared"
            " heartbeat, with an empty tree, no parents and nothing else",
        )

    def is_empty_root(self, commit: str) -> tuple[bool, str]:
        empty_tree = self._empty_tree()
        if not empty_tree:
            return False, "git could not compute the empty tree to compare against"
        problem = self._commit_problem(commit, empty_tree)
        return (not problem), problem

    # --- the rule, one line at a time -----------------------------------------------------

    def _ask(self, *args: str) -> tuple[int, str]:
        return self._run((NO_REPLACE_OBJECTS, *args))

    def _empty_tree(self) -> str:
        code, empty_tree = self._ask("hash-object", "-t", "tree", "/dev/null")
        return empty_tree if code == 0 and _OBJECT_NAME.fullmatch(empty_tree) else ""

    def _line_problem(self, line: str, empty_tree: str) -> str:
        parts = line.rsplit(maxsplit=3)
        if len(parts) != 4:
            return f"{line!r} is not a pre-push line"
        _local_ref, local_object, remote_ref, _remote_object = parts
        if not remote_ref.startswith("refs/"):
            return f"{remote_ref} is not a full ref name"
        if remote_ref.startswith("refs/heads/"):
            return f"{remote_ref} is a branch"
        if remote_ref.startswith("refs/tags/"):
            return f"{remote_ref} is a tag"
        if remote_ref not in self._refs:
            declared = ", ".join(sorted(self._refs)) or "none is declared"
            return f"{remote_ref} is not the declared heartbeat ref ({declared})"
        if not _OBJECT_NAME.fullmatch(local_object):
            return f"{local_object!r} is not an object name"
        if not local_object.strip("0"):
            return f"the push deletes {remote_ref}"
        problem = self._commit_problem(local_object, empty_tree)
        return f"{remote_ref}: {problem}" if problem else ""

    def _commit_problem(self, commit: str, empty_tree: str) -> str:
        code, kind = self._ask("cat-file", "-t", commit)
        if code != 0:
            return f"could not read {commit}"
        if kind != "commit":
            # `cat-file commit` would peel an annotated tag to its commit; asking the type
            # first means a tag object never passes as the commit it points at.
            return f"{commit} is not a commit (it is a {kind})"
        code, body = self._ask("cat-file", "commit", commit)
        if code != 0:
            return f"could not read {commit}"
        header = body.split("\n\n", 1)[0].splitlines()
        if any(field.startswith("parent ") for field in header):
            return f"{commit} has a parent, so it carries history"
        trees = [field.removeprefix("tree ") for field in header if field.startswith("tree ")]
        if trees != [empty_tree]:
            return f"{commit} carries a tree with something in it"
        return self._object_set_problem(commit, empty_tree)

    def _object_set_problem(self, commit: str, empty_tree: str) -> str:
        """The objects a push of `commit` would carry, judged as a set: exactly the commit
        and the empty tree. `rev-list --objects` walks what the pack walks, so a graft that
        gives the commit a parent the raw object does not name is seen here, not missed."""
        code, listed = self._ask("rev-list", "--objects", "--no-object-names", commit)
        if code != 0:
            return f"could not list the objects {commit} would carry"
        carried = listed.split()
        if sorted(carried) != sorted((commit, empty_tree)):
            return (
                f"{commit} would carry {len(carried)} objects, not only itself and the empty"
                " tree (a graft, or history the commit itself does not name)"
            )
        return ""

    # --- the default seam -----------------------------------------------------------------

    def _git(self, args: Sequence[str]) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 B607 - a fixed argv, never a shell
                ["git", *args],
                cwd=self._cwd,
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 127, ""
        return done.returncode, done.stdout.strip()
