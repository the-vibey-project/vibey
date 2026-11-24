# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starts a local MCP server with only the environment variables the person allowed (R7).

A runner starts a `local` server as `python -I -m vibey_runners.common.capabilities.scrubbed_exec
--allow NAME ... -- COMMAND ARGS...` (`LAUNCHER_ARGS`). `-I` is isolated mode: the folder the
server starts in (the run's worktree) is not on `sys.path`, and no `PYTHON*` variable is read, so
a planted `shutil.py` or a `PYTHONSTARTUP` cannot run inside the launcher before it scrubs. The
launcher inherits the runner's environment, keeps only
the `--allow` names it holds, and replaces itself with the command. The values therefore travel
only through the inherited environment and the child's: never an argv, a log or a file. A name
that is absent is skipped. A name that carries a secret (`SECRET_ENV_NAMES`,
`SECRET_ENV_PATTERN`) is refused with exit 78 even though the bundle and the document reader
already refuse it: this is the last place it could still be stopped. The command is resolved on
the inherited `PATH` before scrubbing, so a server need not be given `PATH` to be found.
Declared by `interfaces/scrubbed_exec_interface.py::ScrubbedExecInterface`.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Final, NoReturn, TextIO

from vibey_runners.common.capabilities.bundle import SECRET_ENV_NAMES, SECRET_ENV_PATTERN

LAUNCHER_MODULE: Final = "vibey_runners.common.capabilities.scrubbed_exec"
"""What a runner passes to `python -m` to start a local MCP server through this launcher."""

LAUNCHER_ARGS: Final = ("-I", "-m", LAUNCHER_MODULE)
"""Everything a runner passes to the interpreter before the launcher's own arguments. `-I`
(isolated mode) keeps the server's folder off `sys.path` and ignores every `PYTHON*` variable, so
nothing in the worktree runs before the scrub. Every runner builds its launcher from this."""

EXIT_USAGE: Final = 2
EXIT_SECRET: Final = 78
EXIT_NOT_FOUND: Final = 127
_ALLOW: Final = "--allow"
_SEPARATOR: Final = "--"
_USAGE: Final = "usage: scrubbed_exec [--allow NAME]... -- COMMAND [ARG]...\n"


class ScrubbedExec:
    """Declared by `interfaces/scrubbed_exec_interface.py::ScrubbedExecInterface`."""

    def __init__(
        self,
        # `list[str]`, not `Sequence[str]`: typeshed's `os.execve` takes a list or a tuple only,
        # and the default has to be the real one.
        execve: Callable[[str, list[str], Mapping[str, str]], NoReturn] = os.execve,
        which: Callable[..., str | None] = shutil.which,
        err: TextIO = sys.stderr,
    ) -> None:
        self._execve = execve
        self._which = which
        self._err = err

    def run(self, argv: Sequence[str], environ: Mapping[str, str]) -> int:
        parsed = self._parse(argv)
        if parsed is None:
            self._err.write(_USAGE)
            return EXIT_USAGE
        allow, command = parsed
        for name in allow:
            if name.upper() in SECRET_ENV_NAMES or SECRET_ENV_PATTERN.search(name):
                # Only the name is written; the message holds no lowercase "k" by design, so a
                # test can prove a one-letter value never reaches it.
                self._err.write(
                    f"scrubbed_exec: refused: {name} names a variable that carries a secret; "
                    "a server never gets one\n"
                )
                return EXIT_SECRET
        resolved = self._which(command[0], path=environ.get("PATH"))
        if resolved is None:
            self._err.write(f"scrubbed_exec: command not found: {command[0]}\n")
            return EXIT_NOT_FOUND
        scrubbed = {name: environ[name] for name in allow if name in environ}
        # The command and its argv come from the person's own `[[loops.mcp_servers]]`, resolved
        # above; no shell is involved and the environment is the scrubbed one. bandit does not
        # flag this call through an attribute, so it carries no suppression marker.
        self._execve(resolved, list(command), scrubbed)

    @staticmethod
    def _parse(argv: Sequence[str]) -> tuple[list[str], list[str]] | None:
        """The allowed names and the command, or None when `argv` is malformed: an option other
        than `--allow`, an `--allow` with no name, no `--`, or nothing after it."""
        allow: list[str] = []
        index = 0
        while index < len(argv):
            token = argv[index]
            if token == _SEPARATOR:
                command = list(argv[index + 1 :])
                return (allow, command) if command else None
            if token != _ALLOW or index + 1 >= len(argv):
                return None
            allow.append(argv[index + 1])
            index += 2
        return None


def main() -> NoReturn:
    """Module-level because `python -m vibey_runners.common.capabilities.scrubbed_exec` needs a
    module-level entry point; it only hands the process's argv and environment to the class.
    `sys.stderr` is read here, not at import, so a replaced stream is the one written to."""
    raise SystemExit(ScrubbedExec(err=sys.stderr).run(sys.argv[1:], os.environ))


if __name__ == "__main__":
    main()
