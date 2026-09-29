# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/triaged_delivery.py` implements. Interfaces declare; they never consume.

The bridge takes one triaged GitHub issue at a time into Vibey's delivery queue: it dispatches
a project, drives the normal worker, and publishes the finished project as a pull request. It
reaches the world through three seams -- the forge (`gh`), a command runner (the `vibey` CLI,
`git`, the push gate, `vibey-gh`) and the ticket store -- and writes what it observed to an
evidence directory.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class CommandResultInterface(Protocol):
    """What one command did. `timed_out` means it was stopped, with its process tree."""

    @property
    def returncode(self) -> int: ...

    @property
    def stdout(self) -> str: ...

    @property
    def stderr(self) -> str: ...

    @property
    def timed_out(self) -> bool: ...


class CommandRunnerInterface(Protocol):
    """Runs one command to completion, or stops it and its descendants at `timeout`."""

    def run(
        self, argv: Sequence[str], *, timeout: float | None = None, cwd: Path | None = None
    ) -> CommandResultInterface: ...


class DeliveryEvidenceInterface(Protocol):
    """The latest observed delivery facts, merged per object. Never a completion claim."""

    def project(self, project_id: str, **values: object) -> None: ...

    def ticket(self, issue_number: int, **values: object) -> None: ...

    def last_project(self, project_id: str) -> dict[str, object]:
        """What was last recorded for the project, or an empty mapping."""
        ...

    def last_ticket(self, issue_number: int) -> dict[str, object]:
        """What was last recorded for the ticket, or an empty mapping."""
        ...


class DeliveryBridgeInterface(Protocol):
    """One bounded pass at a time: resume what is in flight, else take the next issue."""

    def run_once(self) -> int:
        """0 when the pass acted or is waiting on in-flight work; 1 when there was nothing
        to take. Resumes before it selects: a dispatched project that is done is published,
        one that can move is driven, and one at a human gate holds the slot."""
        ...

    def drive(self, project_id: str) -> str:
        """Run the worker until the project reaches a gate, a pause, or a step's end. Returns
        the outcome recorded as evidence (`done`, `parked_at_gate`, ...)."""
        ...

    def publish(self, project_id: str, issue_number: int, title: str) -> str | None:
        """Push a DONE project's integration branch and open (or reuse) its pull request.
        The pull request's URL, or None when the project is not done."""
        ...
