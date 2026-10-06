# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A vibey command run on the repository's own GitHub-hosted runners (ADR-0085).

`vibey -w <command>` (or `--workflows`) does not run `<command>` on this machine: it dispatches
`.github/workflows/vibey-remote.yml`, which runs the same command line with vibey on a GitHub
runner and hands back what it printed and its exit code. Every krypton interface reaches the
same path, through the CLI or through the hub's `/api/v1/workflows/runs` routes.

This module is the part with no I/O: which tokens of a command line are vibey's own global
options and so may carry the flag, the command that is sent, the id that finds its run again,
and what a run reports. Pure: no I/O, no clock, no randomness (the caller supplies the id).
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar, Final

from vibey.domain.errors import VibeyError

WORKFLOWS_FLAGS: Final[frozenset[str]] = frozenset({"-w", "--workflows"})
"""The flag that sends a command to the workflows."""

VALUE_OPTIONS: Final[frozenset[str]] = frozenset({"--log-level", "--log-file"})
"""vibey's global options that take a value as the next token."""


class RemoteCommandRefused(VibeyError):
    """A command line that cannot be sent to the workflows as it stands."""


class RemoteState(StrEnum):
    """Where a dispatched command is."""

    QUEUED = "queued"
    """Dispatched; the forge has not shown its run yet, or has not started it."""
    RUNNING = "running"
    """Its run is on a runner."""
    DONE = "done"
    """The command ran; its exit code, output and errors are in the report."""
    FAILED = "failed"
    """The run ended without a report: the runner, not the command, failed."""


@dataclass(frozen=True)
class RemoteCommand:
    """One command line for the workflows: vibey's own arguments, without the flag.

    Declared by `interfaces/remote_command_interface.py::RemoteCommandInterface`."""

    argv: tuple[str, ...]
    request_id: str

    MAX_CHARS: ClassVar[int] = 4000
    """A workflow input carries far more, but a command line past this is not one a person
    types: the cap keeps a dispatch, and the run name it is found by, readable."""

    REQUEST_ID: ClassVar[re.Pattern[str]] = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{7,63}")

    def __post_init__(self) -> None:
        if not self.argv:
            raise RemoteCommandRefused("name a command to run on the workflows: vibey -w <command>")
        if any(token in WORKFLOWS_FLAGS for token in self.argv):
            raise RemoteCommandRefused("a command sent to the workflows cannot itself carry -w")
        if any("\x00" in token for token in self.argv):
            raise RemoteCommandRefused("a command line cannot carry a NUL character")
        if sum(len(token) + 1 for token in self.argv) > self.MAX_CHARS:
            raise RemoteCommandRefused(
                f"a command sent to the workflows is at most {self.MAX_CHARS} characters"
            )
        self.run_name_for(self.request_id)

    @property
    def run_name(self) -> str:
        """The run's name on the forge, which is how the run is found again."""
        return self.run_name_for(self.request_id)

    @classmethod
    def run_name_for(cls, request_id: str) -> str:
        """The run name a request id gives, refusing anything that is not a request id (it
        reaches the forge's query, so it is held to a plain shape first)."""
        if not cls.REQUEST_ID.fullmatch(request_id):
            raise RemoteCommandRefused(f"not a request id: {request_id!r}")
        return f"vibey {request_id}"


@dataclass(frozen=True)
class WorkflowRun:
    """One run of the remote-command workflow, as the forge shows it."""

    run_id: int
    status: str
    """The forge's word: `queued`, `in_progress`, `completed`, and the like."""
    conclusion: str | None
    url: str


@dataclass(frozen=True)
class RemoteReport:
    """What the runner handed back: the command's exit code and what it printed."""

    exit_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class RemoteStatus:
    """What one dispatched command has come to. `exit_code` and the output are set once the
    state is `DONE`; `url` once the forge shows the run."""

    request_id: str
    state: RemoteState
    url: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    detail: str = ""

    @property
    def finished(self) -> bool:
        return self.state in (RemoteState.DONE, RemoteState.FAILED)

    def as_dict(self) -> dict[str, object]:
        return {
            "request_id": self.request_id,
            "state": self.state.value,
            "url": self.url,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "detail": self.detail,
        }


class WorkflowsInvocation:
    """Reads `-w`/`--workflows` out of vibey's leading global options. Pure.

    Declared by `interfaces/remote_command_interface.py::WorkflowsInvocationInterface`.

    Only the options before the command are vibey's own; a `-w` after it belongs to the
    command (the flag means something else there, or nothing), so it is left alone. A
    cluster of short flags (`-vw`) is read flag by flag, as the parser does.
    """

    def split(self, argv: Sequence[str]) -> tuple[bool, tuple[str, ...]]:
        """Whether the command line asks for the workflows, and the command line without
        the flag."""
        remote = False
        kept: list[str] = []
        tokens = list(argv)
        index = 0
        while index < len(tokens):
            arg = tokens[index]
            if arg == "--" or not arg.startswith("-") or arg == "-":
                break
            if arg in WORKFLOWS_FLAGS:
                remote = True
            elif arg in VALUE_OPTIONS:
                kept.extend(tokens[index : index + 2])
                index += 1
            elif not arg.startswith("--") and len(arg) > 2 and "w" in arg[1:]:
                remote = True
                rest = arg[1:].replace("w", "")
                if rest:
                    kept.append(f"-{rest}")
            else:
                kept.append(arg)
            index += 1
        kept.extend(tokens[index:])
        return remote, tuple(kept)


WORKFLOWS_INVOCATION: Final[WorkflowsInvocation] = WorkflowsInvocation()
