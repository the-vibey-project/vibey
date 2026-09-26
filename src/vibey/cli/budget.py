# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey budget`: a project's caps and this cycle's spend against them, and a way to
add, change and remove the caps after the project exists.

`vibey budget [PROJECT_ID]` shows one project (the latest by default); `--all` shows
every project, newest first. `set` gives a cap a value and `clear` removes one, which
leaves the project uncapped for it. The caps stay in the project's config, the one place
the brake reads them, and the spend is the same ledger sum `vibey cost` and the worker
use: this command is never a second opinion. Every change is recorded on the project's
ledger as `BudgetCapChanged`, in the same transaction as the config it describes, and
the history shown here is read back from those events.

The human reading is one short block per project; `--json` is the same budget for a
program -- the shape the VS Code extension reads, a fixed contract (doctrine 7).
"""

import asyncio
import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC
from pathlib import Path
from typing import Annotated, ClassVar, Final
from uuid import UUID

import typer
from typer.core import TyperGroup

from vibey.application.dto import BudgetChange, ProjectBudget
from vibey.application.project_budget import BUDGET_GATE_KIND
from vibey.bootstrap import AppResources, build_app
from vibey.cli.errors import guard
from vibey.cli.gate_answers import ANY_ANSWER, GateAnswerCommands
from vibey.cli.interfaces.budget_interface import BudgetCommandInterface, BudgetPresenterInterface
from vibey.cli.interfaces.gate_answers_interface import GateAnswerCommandsInterface
from vibey.cli.ultra import ULTRA
from vibey.domain.budget_caps import CAP_CHANGE_PLANNER, CapField
from vibey.domain.errors import InvalidBudgetChange
from vibey.domain.interfaces.budget_caps_interface import (
    CapChangePlannerInterface,
    CapHistoryEntryInterface,
)

_CAP_NAMES: Final = {
    CapField.MAX_CYCLE_DOLLARS.value: "dollar cap",
    CapField.MAX_CYCLE_TURNS.value: "turn cap",
}

RESUME_UNDER_THE_STORED_CAPS: Final[GateAnswerCommandsInterface] = GateAnswerCommands(
    {BUDGET_GATE_KIND: ANY_ANSWER}
)
"""`vibey gates`' renderer, with the one rule that differs after a cap change. There it
answers a `budget_exhausted` gate with a grant for that one job; once the stored cap has
changed, any answer resumes the job under it, so the answer is `--raw '{}'`."""


class BudgetPresenter:
    """Renders budgets for a person as short plain blocks, or as the JSON contract."""

    def __init__(self, answers: GateAnswerCommandsInterface = RESUME_UNDER_THE_STORED_CAPS) -> None:
        self._answers = answers

    def budget(self, budget: ProjectBudget) -> list[str]:
        ledger = budget.budget
        dollar_cap = (
            f"cap {self._money(ledger.max_dollars)}" if ledger.max_dollars is not None else "no cap"
        )
        turn_cap = f"cap {ledger.max_turns}" if ledger.max_turns is not None else "no cap"
        lines = [
            f"{budget.name} ({budget.project_id}), cycle {budget.cycle}",
            f"  dollars: ${ledger.dollars_spent:.2f} spent this cycle; {dollar_cap}",
            f"  turns:   {ledger.turns_spent} spent this cycle; {turn_cap}",
        ]
        reached = [
            name
            for name, hit in (
                ("dollar cap", ledger.dollars_exhausted),
                ("turn cap", ledger.turns_exhausted),
            )
            if hit
        ]
        if reached:
            verb = "is" if len(reached) == 1 else "are"
            lines.append(
                f"  The {' and the '.join(reached)} {verb} reached: the next BUILD session "
                "will park a budget_exhausted gate."
            )
        if budget.history:
            last = budget.history[-1]
            count = len(budget.history)
            lines.append(
                f"  last change: {self._entry(last)}"
                f" ({count} change{'' if count == 1 else 's'} in all)"
            )
        else:
            lines.append("  last change: none since the project was created")
        return lines

    def budgets(self, budgets: Sequence[ProjectBudget]) -> list[str]:
        if not budgets:
            return ["no projects yet; create one with `vibey new <name> --repo <path>`"]
        lines: list[str] = []
        for budget in budgets:
            if lines:
                lines.append("")
            lines.extend(self.budget(budget))
        return lines

    def document(self, budget: ProjectBudget) -> dict[str, object]:
        ledger = budget.budget
        return {
            "project_id": str(budget.project_id),
            "name": budget.name,
            "cycle": budget.cycle,
            "caps": {
                CapField.MAX_CYCLE_DOLLARS.value: ledger.max_dollars,
                CapField.MAX_CYCLE_TURNS.value: ledger.max_turns,
            },
            "spend": {"dollars": ledger.dollars_spent, "turns": ledger.turns_spent},
            "exhausted": budget.exhausted,
            "history": [
                {
                    "at": entry.at.isoformat(),
                    "by": entry.by,
                    "field": entry.field,
                    "old": entry.old,
                    "new": entry.new,
                }
                for entry in budget.history
            ],
        }

    def budget_json(self, budget: ProjectBudget) -> str:
        return json.dumps(self.document(budget), indent=2)

    def budgets_json(self, budgets: Sequence[ProjectBudget]) -> str:
        return json.dumps([self.document(budget) for budget in budgets], indent=2)

    def change(self, change: BudgetChange) -> list[str]:
        if change.changes:
            lines = [f"Changed by {change.by}:"]
            lines.extend(
                f"  {_CAP_NAMES[item.field.value]}: {self._value(item.field.value, item.old)} -> "
                f"{self._value(item.field.value, item.new)}"
                for item in change.changes
            )
        else:
            lines = ["Nothing changed: the caps were already as asked."]
        lines.append("")
        lines.extend(self.budget(change.after))
        if change.parked:
            count = len(change.parked)
            jobs = "1 job is" if count == 1 else f"{count} jobs are"
            lines.append("")
            lines.append(
                f"{jobs} still parked on a budget_exhausted gate. A changed cap applies once "
                f"the gate is answered:"
            )
            lines.extend(f"  {self._answers.command(gate)}" for gate in change.parked)
        return lines

    def _entry(self, entry: CapHistoryEntryInterface) -> str:
        name = _CAP_NAMES.get(entry.field, entry.field)
        old = self._value(entry.field, entry.old)
        new = self._value(entry.field, entry.new)
        at = entry.at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
        who = f"by {entry.by}, " if entry.by else ""
        return f"{name} {old} -> {new}, {who}{at}"

    def _value(self, field: str, value: object) -> str:
        if value is None:
            return "none"
        if (
            field == CapField.MAX_CYCLE_DOLLARS.value
            and isinstance(value, int | float)
            and not isinstance(value, bool)
        ):
            return self._money(float(value))
        return str(value)

    @staticmethod
    def _money(amount: float) -> str:
        """Cents, unless the cap was set finer than that: a cap is shown as set."""
        return f"${amount:.2f}" if round(amount, 2) == amount else f"${amount}"


BUDGET_PRESENTER: Final[BudgetPresenterInterface] = BudgetPresenter()


class BudgetCommand:
    """Checks what it can before touching the database, opens the app, asks the one
    budget service, prints."""

    def __init__(
        self,
        *,
        presenter: BudgetPresenterInterface = BUDGET_PRESENTER,
        planner: CapChangePlannerInterface = CAP_CHANGE_PLANNER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._planner = planner
        self._open_app = open_app

    async def show(self, project_id: UUID | None, *, all_projects: bool, as_json: bool) -> None:
        if all_projects and project_id is not None:
            raise typer.BadParameter(
                "name a PROJECT_ID or give --all, not both", param_hint="--all"
            )
        async with self._open_app() as resources:
            if all_projects:
                budgets = await resources.project_budgets.show_all()
                text = (
                    self._presenter.budgets_json(budgets)
                    if as_json
                    else "\n".join(self._presenter.budgets(budgets))
                )
            else:
                target = await self._project(resources, project_id)
                budget = await resources.project_budgets.show(target)
                text = (
                    self._presenter.budget_json(budget)
                    if as_json
                    else "\n".join(self._presenter.budget(budget))
                )
        typer.echo(text)

    async def set(
        self,
        project_id: UUID | None,
        *,
        max_dollars: float | None,
        max_turns: int | None,
        by: str | None,
    ) -> None:
        self._usage(
            lambda: self._planner.setting(max_dollars=max_dollars, max_turns=max_turns),
            "--max-cycle-dollars / --max-cycle-turns",
        )
        self._usage(lambda: self._planner.actor(by, account=""), "--by")
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            change = await resources.project_budgets.set_caps(
                target, max_dollars=max_dollars, max_turns=max_turns, by=by
            )
        typer.echo("\n".join(self._presenter.change(change)))

    async def clear(
        self,
        project_id: UUID | None,
        *,
        dollars: bool,
        turns: bool,
        both: bool,
        by: str | None,
    ) -> None:
        caps = frozenset(
            cap
            for cap, named in (
                (CapField.MAX_CYCLE_DOLLARS, dollars or both),
                (CapField.MAX_CYCLE_TURNS, turns or both),
            )
            if named
        )
        self._usage(lambda: self._planner.clearing(caps), "--dollars / --turns / --all")
        self._usage(lambda: self._planner.actor(by, account=""), "--by")
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            change = await resources.project_budgets.clear_caps(target, caps, by=by)
        typer.echo("\n".join(self._presenter.change(change)))

    @staticmethod
    def _usage(check: Callable[[], object], hint: str) -> None:
        """A request vibey would refuse is a usage error (exit 2), found before anything
        is opened, rather than a refusal (exit 3) found after."""
        try:
            check()
        except InvalidBudgetChange as exc:
            raise typer.BadParameter(str(exc), param_hint=hint) from exc

    @staticmethod
    async def _project(resources: AppResources, project_id: UUID | None) -> UUID:
        # The resolution, messages and exit codes every project-scoped command gives
        # (`vibey cost`, `vibey queue`): the latest project when none is named, and exit
        # 1 when there is none or the id names nothing. They share no helper to call
        # yet; this is the same rule, not a new one.
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


BUDGET: Final[BudgetCommandInterface] = BudgetCommand()
"""The command `vibey budget` runs. Annotated with the interface so `mypy --strict`
checks the class against its declared seam."""


class ShowByDefault(TyperGroup):
    """`vibey budget` with no subcommand shows a budget.

    A group reads its own arguments before its subcommand's name, so an optional
    PROJECT_ID on the group itself would swallow `set` and `clear`. So the group takes
    none: anything that is not a subcommand's name or `--help` -- a project id, `--json`,
    `--all`, or nothing at all -- is handed to `show`.
    """

    DEFAULT: ClassVar[str] = "show"

    # The base names the context of the click typer vendors privately (`typer._click`);
    # `typer.Context`, the public name, is the context typer hands every command.
    def parse_args(self, ctx: typer.Context, args: list[str]) -> list[str]:  # type: ignore[override]
        if not args or (args[0] not in self.commands and args[0] not in ctx.help_option_names):
            args = [self.DEFAULT, *args]
        return super().parse_args(ctx, args)


budget_app = typer.Typer(
    name="budget",
    cls=ShowByDefault,
    help="See a project's caps and this cycle's spend against them, and add, change or "
    "remove the caps. With no subcommand, shows the latest project's budget.",
)

ProjectArgument = Annotated[
    UUID | None,
    typer.Argument(help="The project; defaults to the most recently created one."),
]
ByOption = Annotated[
    str | None,
    typer.Option(
        "--by",
        help="The name this change is recorded under, for a tool that runs the command "
        "(the VS Code extension says vibey-vscode). Defaults to the account running it. A "
        "label for the record, not a permission: the account is recorded beside it.",
    ),
]


# Module-level functions from here down because typer builds a command from a plain
# function's signature. They hold no logic; the command class does.
@budget_app.command("show")
def budget_show(
    project_id: ProjectArgument = None,
    all_projects: Annotated[
        bool, typer.Option("--all", help="Every project's budget, newest project first.")
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print JSON instead: one object, or with --all an array of them "
            "(project_id, name, cycle, caps, spend, exhausted, history).",
        ),
    ] = False,
) -> None:
    """Show the caps, this cycle's spend against them, and every change to the caps."""
    with guard():
        asyncio.run(BUDGET.show(project_id, all_projects=all_projects, as_json=as_json))


@budget_app.command("set")
def budget_set(
    project_id: ProjectArgument = None,
    max_cycle_dollars: Annotated[
        float | None,
        typer.Option(
            "--max-cycle-dollars",
            help="Cap on engine spend per cycle, in dollars: a number above zero.",
        ),
    ] = None,
    max_cycle_turns: Annotated[
        int | None,
        typer.Option(
            "--max-cycle-turns", help="Cap on engine turns per cycle: a whole number above zero."
        ),
    ] = None,
    by: ByOption = None,
) -> None:
    """Add or change a cap.

    A cap at or below this cycle's spend is allowed: the next BUILD session then parks a
    budget_exhausted gate, and the command says so.
    """
    with guard():
        asyncio.run(
            BUDGET.set(project_id, max_dollars=max_cycle_dollars, max_turns=max_cycle_turns, by=by)
        )


@budget_app.command("clear")
def budget_clear(
    project_id: ProjectArgument = None,
    dollars: Annotated[bool, typer.Option("--dollars", help="Remove the dollar cap.")] = False,
    turns: Annotated[bool, typer.Option("--turns", help="Remove the turn cap.")] = False,
    both: Annotated[bool, typer.Option("--all", help="Remove both caps.")] = False,
    by: ByOption = None,
) -> None:
    """Remove a cap: the project is uncapped for it, as if it had never been set."""
    with guard():
        asyncio.run(BUDGET.clear(project_id, dollars=dollars, turns=turns, both=both, by=by))


@budget_app.command("no-cap")
def budget_no_cap(
    project_id: ProjectArgument = None,
    by: ByOption = None,
    toml: Annotated[
        Path, typer.Option("--toml", help="The vibey.toml that records the declaration.")
    ] = Path("vibey.toml"),
) -> None:
    """Declare no cap for ULTRA runs: two warnings and a typed phrase, in a terminal on
    the host (sub-doctrine 8.b). Withdrawn by `vibey budget cap`."""
    with guard():
        asyncio.run(ULTRA.no_cap(project_id, by=by, toml=toml))


@budget_app.command("cap")
def budget_cap(
    project_id: ProjectArgument = None,
    by: ByOption = None,
    toml: Annotated[
        Path, typer.Option("--toml", help="The vibey.toml that records the declaration.")
    ] = Path("vibey.toml"),
) -> None:
    """Withdraw the no-cap declaration: one action, binding at the next ULTRA pass."""
    with guard():
        asyncio.run(ULTRA.keep_cap(project_id, by=by, toml=toml))
