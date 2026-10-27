# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey engines`: engine health, circuit breakers and selection, as a table or as JSON.

The per-engine document is the one `vibey status --json` already carried under `circuits` (and
the hub's status route returns): `StatusPresenter` now calls this, so the two cannot disagree
about what an engine's health is (doctrine 7). `--json` prints one document on stdout; a
message, such as there being no project, goes to stderr and the exit code is the text form's.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Final
from uuid import UUID

import typer

from vibey.application.dto import EngineHealthRecord
from vibey.bootstrap import AppResources, build_app
from vibey.cli.interfaces.engines_interface import (
    EnginesCommandInterface,
    EnginesPresenterInterface,
)
from vibey.cli.interfaces.project_target_interface import ProjectTargetInterface
from vibey.cli.project_target import PROJECT_TARGET
from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository


class EnginesPresenter:
    """Renders engine health rows."""

    def document(self, record: EngineHealthRecord) -> dict[str, object]:
        return {
            "engine_id": record.engine_id.value,
            "installed": record.installed,
            "version": record.version,
            "conformance_ok": record.conformance_ok,
            "circuit": self.circuit(record),
            "capacity_state": str(record.capacity_state) if record.capacity_state else None,
            "consecutive_fail": record.consecutive_fail,
            "cost_usd_cycle": record.cost_usd_cycle,
            "selected_count": record.selected_count,
        }

    @staticmethod
    def circuit(record: EngineHealthRecord) -> str:
        return record.circuit.value if hasattr(record.circuit, "value") else str(record.circuit)

    def table(self, records: Sequence[EngineHealthRecord]) -> list[str]:
        lines = [
            f"{'ENGINE':<12} {'VERSION':<10} {'CIRCUIT':<10} "
            f"{'FAILS':<6} {'SELECTED':<10} {'COST':<8}",
            "-" * 60,
        ]
        lines += [
            f"{r.engine_id:<12} {r.version or '-':<10} {self.circuit(r):<10} "
            f"{r.consecutive_fail:<6} {r.selected_count:<10} ${r.cost_usd_cycle:<7.2f}"
            for r in records
        ]
        return lines

    def engines_json(self, project_id: UUID, records: Sequence[EngineHealthRecord]) -> str:
        document = {
            "project_id": str(project_id),
            "engines": [self.document(record) for record in records],
        }
        return json.dumps(document, indent=2)


ENGINES_PRESENTER: Final[EnginesPresenterInterface] = EnginesPresenter()


class EnginesCommand:
    """Finds the project, reads its engine health rows, prints them."""

    def __init__(
        self,
        *,
        presenter: EnginesPresenterInterface = ENGINES_PRESENTER,
        target: ProjectTargetInterface = PROJECT_TARGET,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._target = target
        self._open_app = open_app

    async def run(self, project_id: UUID | None, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            if project_id is None:
                project_id = (await self._target.latest(resources, as_json=as_json)).project_id
            health = PostgresEngineHealthRepository(resources.ledger._pool)
            records = await health.list_for_project(project_id)
        if as_json:
            typer.echo(self._presenter.engines_json(project_id, records))
        elif not records:
            typer.echo("no engines recorded for project")
        else:
            typer.echo("\n".join(self._presenter.table(records)))


ENGINES: Final[EnginesCommandInterface] = EnginesCommand()
"""The command `vibey engines` runs. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
