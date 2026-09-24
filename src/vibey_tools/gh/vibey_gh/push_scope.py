# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The pre-push gate's scope: a push that carries no code has nothing for it to judge.

The pre-push stage exists to judge code on its way off the machine: type-check it, test it,
audit what it depends on. Some pushes carry none. The sovereign heartbeat (doctrine 8.a) is
an empty tree with no parents, pushed to a ref outside `refs/heads/`: no diff, no file, no
dependency. Running the full suite over it is not diligence, it is a timer that cannot
finish inside its own interval -- measured at more than two minutes against 1.2 seconds.

The old answer was for the CALLER to skip the gate with `git push --no-verify`. That is a
means whose purpose is to make a check stop applying, which sub-doctrine 12.d forbids with no
exceptions, and it skips the gate for whatever the push happens to carry. This is the other
answer: the gate applies its own rule to what git hands it, and that rule is narrow enough to
state in one sentence. A push carries no code only when **every** ref it updates is outside
`refs/heads/` and `refs/tags/` and **every** commit it sends is the empty tree with no parents.

Three properties make it safe to trust:

- **It reads git's own list, all of it.** The refs come from the pre-push hook's standard
  input, which git writes and which is the only place the list is complete: the pre-commit
  framework reads only the first line (`_pre_push_ns` in pre-commit 4.6.2) and exports only
  that ref, so a check reading the framework's variables would pass a push whose first ref is
  a heartbeat and whose second is a branch.
- **It asks git about the objects**, never the caller. There is no flag, variable or file
  that says "skip"; there is only what the objects are. The empty tree's id is computed by
  the repository, so a SHA-256 repository is judged by its own format.
- **It fails closed.** A branch, a tag, a tree with anything in it, a commit with a parent, a
  deletion, an object that is not a commit, a line git would never write, an object git
  cannot read, no refs at all -- every one carries code, and the full gate runs.

The hook skips its heavy stage only on the exact `NO_CODE` token on standard output, so a
`vibey-gh` too old to know this command, or one that crashes, runs the full gate.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from vibey_gh.interfaces.push_scope_interface import PushScopeInterface

__all__ = ["NO_CODE", "PushScope", "PushVerdict"]

# What `vibey-gh push-scope` prints, and all it prints, when a push carries no code. The hook
# compares standard output against it exactly; nothing else skips the heavy stage.
NO_CODE = "carries-no-code"

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

    `git` is the seam: it takes the arguments after `git` and returns the exit status and the
    stripped standard output. The default runs git in `cwd`, which inside a hook is the top
    of the working tree git is pushing from.
    """

    def __init__(self, *, git: GitRunner | None = None, cwd: str | Path | None = None) -> None:
        self._cwd = cwd
        self._run = git or self._git

    def judge(self, pre_push_input: str) -> PushVerdict:
        lines = [line for line in pre_push_input.splitlines() if line.strip()]
        if not lines:
            return PushVerdict(True, "no refs were given, which proves nothing about the push")
        code, empty_tree = self._run(("hash-object", "-t", "tree", "/dev/null"))
        if code != 0 or not _OBJECT_NAME.fullmatch(empty_tree):
            return PushVerdict(True, "git could not compute the empty tree to compare against")
        refs = []
        for line in lines:
            problem = self._line_problem(line, empty_tree)
            if problem:
                return PushVerdict(True, problem)
            refs.append(line.rsplit(maxsplit=3)[2])
        count = "1 ref" if len(refs) == 1 else f"{len(refs)} refs"
        return PushVerdict(
            False,
            f"this push carries no code: {count} outside refs/heads/ and refs/tags/"
            f" ({', '.join(refs)}), each an empty tree with no parents",
        )

    def is_empty_root(self, commit: str) -> tuple[bool, str]:
        code, empty_tree = self._run(("hash-object", "-t", "tree", "/dev/null"))
        if code != 0 or not _OBJECT_NAME.fullmatch(empty_tree):
            return False, "git could not compute the empty tree to compare against"
        problem = self._commit_problem(commit, empty_tree)
        return (not problem), problem

    # --- the rule, one line at a time -----------------------------------------------------

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
        if not _OBJECT_NAME.fullmatch(local_object):
            return f"{local_object!r} is not an object name"
        if not local_object.strip("0"):
            return f"the push deletes {remote_ref}"
        problem = self._commit_problem(local_object, empty_tree)
        return f"{remote_ref}: {problem}" if problem else ""

    def _commit_problem(self, commit: str, empty_tree: str) -> str:
        code, kind = self._run(("cat-file", "-t", commit))
        if code != 0:
            return f"could not read {commit}"
        if kind != "commit":
            # `cat-file commit` would peel an annotated tag to its commit; asking the type
            # first means a tag object never passes as the commit it points at.
            return f"{commit} is not a commit (it is a {kind})"
        code, body = self._run(("cat-file", "commit", commit))
        if code != 0:
            return f"could not read {commit}"
        header = body.split("\n\n", 1)[0].splitlines()
        if any(field.startswith("parent ") for field in header):
            return f"{commit} has a parent, so it carries history"
        trees = [field.removeprefix("tree ") for field in header if field.startswith("tree ")]
        if trees != [empty_tree]:
            return f"{commit} carries a tree with something in it"
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
