# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey cost`: the cycle's spend against the caps the budget brake enforces.

The caps, the spend and whether a cap is reached are `vibey budget show --json`'s own document
(`BudgetPresenter.document`), not a second reading of them, with `history` left out because
`cost` has never shown it. The per-engine figure is each engine's metered BUILD-session spend,
which accumulates across cycles and leaves DESIGN out; the document names it
`cost_usd_all_cycles` for that reason, where the database column (and `engines --json`, and the
hub, which share it) call it `cost_usd_cycle`. The count is how often rotation selected the
engine, which is not a turn count.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Final
from uuid import UUID

import typer

from vibey.application.dto import EngineHealthRecord, ProjectBudget
from vibey.bootstrap import AppResources, build_app
from vibey.cli.budget import BUDGET_PRESENTER
from vibey.cli.interfaces.cost_interface import CostCommandInterface, CostPresenterInterface
from vibey.cli.interfaces.project_target_interface import ProjectTargetInterface
from vibey.cli.project_target import PROJECT_TARGET
from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository


class CostPresenter:
    """Renders spend against caps."""

    def lines(self, budget: ProjectBudget, records: Sequence[EngineHealthRecord]) -> list[str]:
        ledger = budget.budget
        dollar_cap = (
            f"${ledger.max_dollars:.2f}" if ledger.max_dollars is not None else "none (uncapped)"
        )
        turn_cap = str(ledger.max_turns) if ledger.max_turns is not None else "none"
        lines = [
            f"Project: {budget.name} (Cycle {budget.cycle})",
            f"Cycle spend:      ${ledger.dollars_spent:.2f} ({ledger.turns_spent} turns)",
            f"Cycle dollar cap: {dollar_cap}",
            f"Cycle turn cap:   {turn_cap}",
        ]
        if ledger.any_exhausted:
            lines.append("Cap reached: the next BUILD session parks a budget_exhausted gate.")
        lines += ["", "Per-engine (BUILD sessions, all cycles):"]
        lines += [
            f"  • {r.engine_id}: ${r.cost_usd_cycle:.2f} ({r.selected_count} selections)"
            for r in records
        ]
        return lines

    def cost_json(self, budget: ProjectBudget, records: Sequence[EngineHealthRecord]) -> str:
        document = BUDGET_PRESENTER.document(budget)
        del document["history"]
        document["engines"] = [
            {
                "engine_id": r.engine_id.value,
                "cost_usd_all_cycles": r.cost_usd_cycle,
                "selected_count": r.selected_count,
            }
            for r in records
        ]
        return json.dumps(document, indent=2)


COST_PRESENTER: Final[CostPresenterInterface] = CostPresenter()


class CostCommand:
    """Finds the project, reads its budget and engine rows, prints them."""

    def __init__(
        self,
        *,
        presenter: CostPresenterInterface = COST_PRESENTER,
        target: ProjectTargetInterface = PROJECT_TARGET,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._target = target
        self._open_app = open_app

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            if project_id is None:
                project = await self._target.latest(resources, as_json=as_json)
            else:
                project = await self._target.get(resources, project_id, as_json=as_json)
            # The brake's own numbers, not a second opinion (issue #210): the caps through the
            # one parser the worker uses and the spend from the ledger sum the worker checks
            # before every BUILD session, read through the one budget reader `vibey budget`
            # shows.
            budget = await resources.project_budgets.show(project.project_id)
            health = PostgresEngineHealthRepository(resources.ledger._pool)
            records = await health.list_for_project(project.project_id)
        if as_json:
            typer.echo(self._presenter.cost_json(budget, records))
        else:
            typer.echo("\n".join(self._presenter.lines(budget, records)))


COST: Final[CostCommandInterface] = CostCommand()
"""The command `vibey cost` runs. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
