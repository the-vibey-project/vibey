# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam every call to the forge's command-line client goes through (vibey ADR-0016).

vibey-gh grew seven private ways to run `gh`, and they disagree about what a failure is:
one raises, one reports a boolean, one returns a problem string so that "could not ask" is
never read as "nothing there". Each caller depends on the answer its own runner gives, so
unifying them into one shape would change behaviour, and a transport that changes
behaviour cannot be adopted one module at a time. This declares one transport that gives
all three answers, each exactly as the runner it replaces gives it today.

It names what a call returns, not which forge it reaches. Choosing between forges is a
later concern of the platform abstraction, and belongs with whatever reads that choice.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from os import PathLike
from typing import Any, Protocol, TypeAlias, runtime_checkable

# A working directory as the callers already hold one: `GhConfig.root` is a `Path`.
WorkingDirectory: TypeAlias = str | PathLike[str]


@runtime_checkable
class GhTransportInterface(Protocol):
    """Runs the forge's client with an argument vector this process built itself."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """The completed process, whatever it exited with. Never raises on a non-zero exit.

        `args` follows the executable, so `["pr", "view", "7"]` runs `gh pr view 7`. Without
        `cwd` the call runs where this process runs; without `stdin` the child inherits
        this process's standard input, exactly as a bare `subprocess.run` would. A missing
        executable raises `FileNotFoundError`, as it always has.
        """
        ...

    def json(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> Any:
        """The decoded JSON the call printed, or `None` when it printed nothing.

        Raises `RuntimeError` naming the command and its stderr on a non-zero exit, and
        lets a `json.JSONDecodeError` through when the output is not JSON. Any, not object:
        the shape differs per subcommand, and callers index into it.
        """
        ...

    def probe(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
        strip: bool = True,
        with_stderr: bool = False,
    ) -> tuple[bool, str]:
        """Whether the call exited zero, and what it printed. Never raises on the exit.

        The two probes the tree runs today disagree on what "what it printed" means, and
        each caller reads its own: promotion parses a stripped stdout as data, while the
        merge train searches stdout and stderr together, verbatim. The defaults are the
        first; `strip=False, with_stderr=True` is the second.
        """
        ...

    def survey(
        self,
        args: Sequence[str],
        *,
        cwd: WorkingDirectory | None = None,
        stdin: str | None = None,
    ) -> tuple[list[Any] | dict[str, Any], str]:
        """The decoded list or object, and a problem that is empty exactly when it answered.

        Never raises. A missing client, a non-zero exit, output that is not JSON, and JSON
        that is neither a list nor an object each come back as `[]` with a sentence saying
        which, so a caller reporting on the forge can say it could not look rather than
        that it looked and found nothing.
        """
        ...
