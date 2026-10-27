# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worked examples at the end of a command's `--help` (#1687).

`HelpLayout` (#1684) gave the root help its examples. This gives six commands theirs: `new`,
`answer`, `gates`, `projects`, `doctor` and `watch`, the ones a newcomer reaches for first.
The examples are one table, so they are read in one place, and `problems` resolves every line
against the real command tree with each command's own parser (never calling its callback, so
nothing runs and no database is needed). An example whose command or flag has gone is a failing
test rather than help text that quietly stopped being true (sub-doctrine 12.e).
"""

from __future__ import annotations

import shlex
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from typer.main import get_command, get_command_name

from vibey.cli.interfaces.command_examples_interface import CommandExamplesInterface

if TYPE_CHECKING:
    import typer

__all__ = ["EXAMPLES", "REQUIRED", "CommandExamples", "Example"]

#: The nil UUID stands in for a gate id. It parses; the note says where the real one comes from.
GATE_ID = "00000000-0000-0000-0000-000000000000"

#: At most this many examples end any one command's help.
MOST_PER_COMMAND = 2


@dataclass(frozen=True)
class Example:
    """One runnable line, and the sentence that says what it does."""

    command: str
    line: str
    note: str


EXAMPLES: tuple[Example, ...] = (
    Example("new", "vibey new my-app", "Start a project and its first design interview."),
    Example(
        "new",
        'vibey new my-app --intake "Add a /health endpoint" --max-cycle-dollars 5',
        "Seed the design with a task, and cap spending at 5 dollars a cycle.",
    ),
    Example("projects", "vibey projects", "List every project, newest first."),
    Example("projects", "vibey projects --json", "The same, as JSON for a script."),
    Example(
        "gates", "vibey gates", "List what is waiting on you, and the command that answers it."
    ),
    Example("gates", "vibey gates --json", "The same, as JSON for a script."),
    Example(
        "answer",
        f"vibey answer {GATE_ID} --defaults",
        "Accept every default on an interview gate (use the id `vibey gates` prints).",
    ),
    Example(
        "answer",
        f"vibey answer {GATE_ID} --verdict accept",
        "Accept a review gate (use the id `vibey gates` prints).",
    ),
    Example("watch", "vibey watch", "Follow the work live."),
    Example("watch", "vibey watch --replay --speed 4", "Replay the ledger at four times speed."),
    Example("doctor", "vibey doctor", "Check this machine is ready: PostgreSQL, engines, auth."),
    Example(
        "doctor",
        "vibey doctor --conformance --engine claudeloop",
        "Run the conformance suite against one engine.",
    ),
)

#: The commands the issue names; each must keep at least one example.
REQUIRED: tuple[str, ...] = ("new", "answer", "gates", "projects", "doctor", "watch")


class CommandExamples(CommandExamplesInterface):
    """Implements `CommandExamplesInterface` over a table of examples."""

    def __init__(
        self, examples: Sequence[Example] = EXAMPLES, required: Sequence[str] = REQUIRED
    ) -> None:
        self._examples = tuple(examples)
        self._required = tuple(required)

    def _for(self, command: str) -> list[Example]:
        return [example for example in self._examples if example.command == command]

    def _epilog(self, command: str) -> str:
        # \b keeps Rich from reflowing the lines into one paragraph (as the root EPILOG does).
        lines = ["\b", "Examples:"]
        for example in self._for(command):
            lines += [f"  {example.line}", f"      {example.note}"]
        return "\n".join(lines)

    def apply(self, app: typer.Typer) -> None:
        wanted = {example.command for example in self._examples}
        for info in app.registered_commands:
            name = info.name or get_command_name(getattr(info.callback, "__name__", ""))
            if name in wanted:
                info.epilog = self._epilog(name)

    def problems(self, app: typer.Typer) -> list[str]:
        # Typer 0.27 vendors its own click, so the group is not an instance of the installed
        # one and its exception types are private: read `commands` by name and catch broadly.
        commands: dict[str, Any] = getattr(get_command(app), "commands", {})
        found: list[str] = []
        for command in self._required:
            if not self._for(command):
                found.append(f"{command}: no example")
        for command in sorted({example.command for example in self._examples}):
            if len(self._for(command)) > MOST_PER_COMMAND:
                found.append(f"{command}: more than {MOST_PER_COMMAND} examples")
        for example in self._examples:
            found += self._check(commands, example)
        return found

    @staticmethod
    def _check(commands: dict[str, Any], example: Example) -> list[str]:
        tokens = shlex.split(example.line)
        if len(tokens) < 2 or tokens[0] != "vibey":
            return [f"{example.line!r}: an example starts with 'vibey COMMAND'"]
        if tokens[1] != example.command:
            return [f"{example.line!r}: filed under {example.command!r} but runs {tokens[1]!r}"]
        command = commands.get(tokens[1])
        if command is None:
            return [f"{example.line!r}: there is no command {tokens[1]!r}"]
        try:
            # make_context parses the arguments with the command's own parser; only invoke would
            # call its callback, and nothing here does.
            command.make_context(tokens[1], tokens[2:], resilient_parsing=False)
        except Exception as error:  # noqa: BLE001 - any refusal to parse the line is the finding
            return [f"{example.line!r}: {error}"]
        return []
