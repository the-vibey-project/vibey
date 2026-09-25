# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ultra` and the no-cap path of `vibey budget` (ADR-0063, sub-doctrine 8.b).

`vibey ultra start` runs a project's BUILD passes at ULTRA; `stop` ends the run at the
next pass boundary; `status` shows it. `vibey budget no-cap` declares no cap only
through the whole path, in a terminal on the host:

1. a full-screen warning with the measured cost per hour ("unknown" when unmeasured);
2. the typed phrase `I accept unlimited spending`;
3. a second warning whose default is "Keep a cap";
4. the declaration: `[budget] ultra_no_cap = true` in `./vibey.toml`, and a trusted
   `UltraNoCapChanged` ledger event naming who, when and which device.

It is refused when stdin is not a terminal, and nothing an environment variable says can
declare it. `vibey budget cap` withdraws it in one action.
"""

import asyncio
import json
import sys
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.dto import UltraStatus
from vibey.bootstrap import AppResources, build_app
from vibey.cli.errors import guard
from vibey.domain.ultra import NO_CAP_PHRASE
from vibey.infrastructure.budget_declaration import VibeyTomlBudgetDeclaration
from vibey.infrastructure.interfaces.budget_declaration_interface import (
    BudgetDeclarationInterface,
)

_RULE: Final = "=" * 72


class UltraCommand:
    """Opens the app, asks the one ULTRA service, prints. The warnings are shown here,
    on the host's terminal, before the service records anything."""

    def __init__(
        self,
        *,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
        declaration: BudgetDeclarationInterface | None = None,
        interactive: Callable[[], bool] = sys.stdin.isatty,
        prompt: Callable[[str], str] = lambda text: str(typer.prompt(text, default="")),
        confirm: Callable[[str], bool] = lambda text: bool(typer.confirm(text, default=False)),
        clear: Callable[[], None] = lambda: typer.echo("\033[2J\033[H", nl=False),
    ) -> None:
        self._open_app = open_app
        self._declaration = declaration or VibeyTomlBudgetDeclaration()
        self._interactive = interactive
        self._prompt = prompt
        self._confirm = confirm
        self._clear = clear

    async def status(self, project_id: UUID | None, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            status = await resources.ultra.status(await self._project(resources, project_id))
        typer.echo(self.render(status, as_json=as_json))

    async def start(self, project_id: UUID | None, *, by: str | None) -> None:
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            status = await resources.ultra.start(target, by=by)
        typer.echo(self.render(status, as_json=False))

    async def stop(self, project_id: UUID | None, *, by: str | None) -> None:
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            status = await resources.ultra.stop(target, by=by)
        typer.echo("Stopped: no further ULTRA pass starts.")
        typer.echo(self.render(status, as_json=False))

    async def no_cap(self, project_id: UUID | None, *, by: str | None, toml: Path) -> None:
        if not self._interactive():
            typer.echo(
                "no cap is declared only interactively, in a terminal on the host "
                "(sub-doctrine 8.b); nothing was changed",
                err=True,
            )
            raise typer.Exit(2)
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            before = await resources.ultra.status(target)
            self._clear()
            typer.echo("\n".join(self.first_warning(before)))
            typed = self._prompt(f'Type "{NO_CAP_PHRASE}" to continue')
            if typed.strip() != NO_CAP_PHRASE:
                typer.echo("The phrase did not match. Kept the cap; nothing was changed.")
                raise typer.Exit(1)
            typer.echo("\n".join(self.second_warning()))
            if not self._confirm("Declare no cap? (the default keeps a cap)"):
                typer.echo("Kept the cap; nothing was changed.")
                return
            status = await resources.ultra.declare_no_cap(target, phrase=typed, by=by)
        self._declaration.write(toml, True)
        typer.echo(f"Declared: no cap. Recorded on the ledger and in {toml}.")
        typer.echo("Withdraw it at any time with one command: vibey budget cap")
        typer.echo(self.render(status, as_json=False))

    async def keep_cap(self, project_id: UUID | None, *, by: str | None, toml: Path) -> None:
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            status = await resources.ultra.keep_cap(target, by=by)
        if toml.exists():
            self._declaration.write(toml, False)
        typer.echo("The no-cap declaration is withdrawn: an ULTRA run needs a dollar cap.")
        typer.echo(self.render(status, as_json=False))

    @staticmethod
    def rate(status: UltraStatus) -> str:
        if status.rate_per_hour is None:
            return "unknown (nothing measured yet)"
        return f"${status.rate_per_hour:.2f}/h"

    def first_warning(self, status: UltraStatus) -> list[str]:
        return [
            _RULE,
            "  WARNING: UNLIMITED SPEND",
            _RULE,
            "",
            f"  Project: {status.name} ({status.project_id})",
            f"  Measured cost: {self.rate(status)}",
            f"  Spent this cycle: ${status.dollars_spent:.2f}",
            "",
            "  With no cap, an ULTRA run keeps starting improvement passes until you",
            "  stop it (`vibey ultra stop`). Nothing else ends it. Paid engines bill",
            "  every pass. There is no ceiling on what this can cost.",
            "",
            _RULE,
        ]

    @staticmethod
    def second_warning() -> list[str]:
        return [
            "",
            _RULE,
            "  LAST CHANCE: this removes the only limit on spend for ULTRA runs.",
            "  Answer no (the default) to keep a cap.",
            _RULE,
        ]

    def render(self, status: UltraStatus, *, as_json: bool) -> str:
        if as_json:
            return json.dumps(
                {
                    "project_id": str(status.project_id),
                    "name": status.name,
                    "active": status.active,
                    "no_cap_declared": status.no_cap_declared,
                    "passes_completed": status.passes_completed,
                    "max_dollars": status.max_dollars,
                    "dollars_spent": status.dollars_spent,
                    "rate_per_hour": status.rate_per_hour,
                },
                indent=2,
            )
        cap = (
            f"${status.max_dollars:.2f}"
            if status.max_dollars is not None
            else ("none: UNLIMITED SPEND declared" if status.no_cap_declared else "none")
        )
        lines = [
            f"{status.name} ({status.project_id})",
            f"  ULTRA: {'running' if status.active else 'stopped'}; "
            f"{status.passes_completed} pass(es) completed",
            f"  dollar cap: {cap}; ${status.dollars_spent:.2f} spent this cycle; "
            f"cost {self.rate(status)}",
        ]
        if status.active and status.max_dollars is None and not status.no_cap_declared:
            lines.append(
                "  No dollar cap and no declaration: the next pass waits for one "
                "(`vibey budget set --max-cycle-dollars N` or `vibey budget no-cap`)."
            )
        return "\n".join(lines)

    @staticmethod
    async def _project(resources: AppResources, project_id: UUID | None) -> UUID:
        # The same resolution `vibey budget` gives (cli/budget.py `BudgetCommand._project`).
        if project_id is None:
            latest = await resources.projects.get_latest()
            if latest is None:
                typer.echo("no projects found; create one with `vibey new` first")
                raise typer.Exit(1)
            return latest.project_id
        if await resources.projects.get(project_id) is None:
            typer.echo(f"unknown project {project_id}")
            raise typer.Exit(1)
        return project_id


ULTRA: Final = UltraCommand()

ultra_app = typer.Typer(
    name="ultra",
    help="Run a project's BUILD passes at ULTRA, effort without a ceiling (ADR-0063): "
    "start, stop at the next pass, or show the run.",
    no_args_is_help=True,
)

ProjectArgument = Annotated[
    UUID | None,
    typer.Argument(help="The project; defaults to the most recently created one."),
]
ByOption = Annotated[
    str | None,
    typer.Option("--by", help="The name this control is recorded under; defaults to the account."),
]
TomlOption = Annotated[
    Path,
    typer.Option("--toml", help="The vibey.toml that records the declaration."),
]


# Module-level functions because typer builds a command from a plain function's
# signature. They hold no logic; the command class does.
@ultra_app.command("start")
def ultra_start(project_id: ProjectArgument = None, by: ByOption = None) -> None:
    """Start ULTRA: every BUILD pass runs with no turn limit, pass after pass."""
    with guard():
        asyncio.run(ULTRA.start(project_id, by=by))


@ultra_app.command("stop")
def ultra_stop(project_id: ProjectArgument = None, by: ByOption = None) -> None:
    """Stop ULTRA: no further pass starts. One action, binding at the next pass."""
    with guard():
        asyncio.run(ULTRA.stop(project_id, by=by))


@ultra_app.command("status")
def ultra_status(
    project_id: ProjectArgument = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON instead.")] = False,
) -> None:
    """Show the run: running or stopped, passes, cap, spend and measured cost."""
    with guard():
        asyncio.run(ULTRA.status(project_id, as_json=as_json))
