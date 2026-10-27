# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey --help`: the command list, grouped by what a person came to do (#1665).

The root app registers thirty-four commands and sub-apps in the order they were written,
and each one printed the whole first paragraph of its help, so a newcomer met a flat wall of
sentences with no hint of where to begin. People scan a list before they read it: this lays
the same commands into six titled panels, first the ones a new user needs, each with a
one-line summary, and ends the help with commands that can be copied.

It changes how the list is presented and nothing else. Every command keeps its name, its
options and the full text of its own `--help`; `short_help` and `rich_help_panel` are the
list's alone.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import typer
from typer.main import get_command_name
from typer.models import CommandInfo, TyperInfo

from vibey.cli.interfaces.help_layout_interface import HelpLayoutInterface


@dataclass(frozen=True)
class Entry:
    """One command or sub-app, and the line the list shows for it."""

    name: str
    summary: str


@dataclass(frozen=True)
class Panel:
    """A titled group of the list, in the order its entries are meant to be read."""

    title: str
    entries: tuple[Entry, ...]


# Ordered as a person meets them: set up and start, decide, watch, run, maintain, then the
# tools agents call. A summary is one line that fits beside its name without wrapping.
PANELS: tuple[Panel, ...] = (
    Panel(
        "Start here",
        (
            Entry("doctor", "Check this machine is ready: PostgreSQL, engines, auth"),
            Entry("install", "Install the local dependencies vibey can manage"),
            Entry("new", "Start a project and its first design interview"),
            Entry("projects", "List every project with its phase and open gates"),
            Entry("status", "Show a project, the queue and the engine circuits"),
        ),
    ),
    Panel(
        "Decisions that are yours",
        (
            Entry("gates", "List what is waiting on you, and how to answer it"),
            Entry("answer", "Answer a waiting gate"),
            Entry("design", "Run or resume the design interview"),
            Entry("visual", "Settle the optional visual-design stage"),
            Entry("deploy", "Manage and inspect the three deployment phases"),
        ),
    ),
    Panel(
        "Watch and steer",
        (
            Entry("watch", "Live dashboard: phase, queue, circuits, ledger tail"),
            Entry("queue", "See the job queue and move a job to the front"),
            Entry("engines", "Show engine health, circuit breakers and selection"),
            Entry("loops", "List the loops, their engines and what each can do"),
            Entry("models", "List local model families and what Ollama says each can do"),
            Entry("cost", "Show this cycle's spend against its caps"),
            Entry("budget", "See, set or remove a project's spending caps"),
            Entry("ledger", "Search, export or publish the append-only ledger"),
            Entry("ultra", "Run BUILD passes at ULTRA effort"),
            Entry("retry", "Get a stalled project moving again"),
            Entry("recover", "Return stuck leased jobs to the ready queue"),
            Entry("abandon", "Stop a project for good and record why"),
        ),
    ),
    Panel(
        "Run the machinery",
        (
            Entry("work", "Process one ready design job"),
            Entry("worker", "Run a long-lived worker across every phase"),
            Entry("serve", "Serve the hub API every krypton client uses"),
            Entry("hub", "Pair, list and revoke devices on the hub"),
            Entry("supervisor", "Keep the worker and the delivery bridge running"),
            Entry("driver", "The driver session's failover and handback"),
            Entry("operator", "Run the Kubernetes operator"),
        ),
    ),
    Panel(
        "Maintain",
        (
            Entry("migrate", "Apply database migrations and reconcile grants"),
            Entry("state", "Keep this database and its sealed GitHub copy in step"),
            Entry("sabbath", "Show the Sabbath window on this host"),
            Entry("explain", "Explain an error code: its cause and what to do"),
        ),
    ),
    Panel(
        "Tools for agents",
        (
            Entry("search", "Search the web through vibey's own backend"),
            Entry("fetch", "Read one public web page as plain text"),
            Entry("llm", "Follow the model conversation and its wire log"),
        ),
    ),
)

# Each line is a command that exists as written. `gates` is the way to a gate's id and the
# exact `vibey answer` that answers it, so no `answer` syntax is guessed at here.
EPILOG = """\b
Examples:
  vibey doctor       check this machine is ready
  vibey new my-app   start a project and its first design interview
  vibey gates        see what is waiting on you, and the command that answers it
  vibey watch        follow the work live

\b
Every command takes --help. projects, gates, status, loops, models, engines and cost take --json.
Documentation: https://the-vibey-project.github.io/vibey/main/"""


class HelpLayout(HelpLayoutInterface):
    """Applies `PANELS` and `EPILOG` to a Typer app's command list."""

    def __init__(self, panels: Sequence[Panel] = PANELS, epilog: str = EPILOG) -> None:
        self._epilog = epilog
        self._placement = {
            entry.name: (rank, panel.title, entry)
            for rank, (panel, entry) in enumerate(
                (panel, entry) for panel in panels for entry in panel.entries
            )
        }

    @staticmethod
    def _command_name(command: CommandInfo) -> str:
        """The name Typer gives a command: the one declared, else its callback's, hyphenated."""
        return command.name or get_command_name(getattr(command.callback, "__name__", ""))

    @staticmethod
    def _group_name(group: TyperInfo) -> str:
        """The name a sub-app is mounted under: the one `add_typer` gave, else its own."""
        return (
            group.name or getattr(getattr(group.typer_instance, "info", None), "name", None) or ""
        )

    def _command_names(self, app: typer.Typer) -> list[str]:
        """The names `app` registers: its commands, then its sub-apps."""
        return [self._command_name(c) for c in app.registered_commands] + [
            self._group_name(g) for g in app.registered_groups
        ]

    def unplaced(self, app: typer.Typer) -> list[str]:
        return [name for name in self._command_names(app) if name not in self._placement]

    def _rank(self, name: str) -> int:
        # An unplaced name sorts after every placed one, and keeps its own panel.
        return self._placement[name][0] if name in self._placement else len(self._placement)

    def apply(self, app: typer.Typer) -> None:
        for command in app.registered_commands:
            self._place(command, self._command_name(command))
        for group in app.registered_groups:
            self._place(group, self._group_name(group))
        # A panel prints in the order its first command is registered, so registration order
        # is made the reading order. `sort` is stable: unplaced names keep theirs, last.
        app.registered_commands.sort(key=lambda c: self._rank(self._command_name(c)))
        app.registered_groups.sort(key=lambda g: self._rank(self._group_name(g)))
        app.info.epilog = self._epilog

    def _place(self, target: CommandInfo | TyperInfo, name: str) -> None:
        if name not in self._placement:
            return
        _, title, entry = self._placement[name]
        target.rich_help_panel = title
        target.short_help = entry.summary
