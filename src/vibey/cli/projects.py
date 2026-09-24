# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey projects`: every project, newest first, and how many gates wait on each.

The project id is what every other command takes, and until this there was no command that
printed one after `vibey new` had. The human reading is a small table; `--json` is the same
list for a program, an array of objects whose keys the VS Code extension reads (doctrine 7).
An empty list is an answer, not a failure: both forms exit 0.
"""

import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC
from typing import Final
from uuid import UUID

import typer

from vibey.application.dto import ProjectRecord
from vibey.bootstrap import AppResources, build_app
from vibey.cli.interfaces.projects_interface import (
    ProjectsCommandInterface,
    ProjectsPresenterInterface,
)
from vibey.domain.phase import Phase, StoredPhase


class ProjectsPresenter:
    """Renders projects as a small plain table for a person, or as JSON for a program."""

    HEADERS: Final = ("NAME", "PHASE", "CYCLE", "OPEN GATES", "CREATED (UTC)", "PROJECT ID")

    def projects(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> list[str]:
        if not projects:
            return ["no projects yet; create one with `vibey new <name> --repo <path>`"]
        rows = [self.HEADERS, *(self._row(project, open_gates) for project in projects)]
        widths = [max(len(row[column]) for row in rows) for column in range(len(self.HEADERS))]
        lines = [
            "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True)).rstrip()
            for row in rows
        ]
        count = len(projects)
        summary = f"{count} project{'' if count == 1 else 's'}, newest first."
        waiting = sum(open_gates.get(project.project_id, 0) for project in projects)
        if waiting:
            summary += (
                f" {waiting} open gate{' is' if waiting == 1 else 's are'} waiting for your "
                "answer: `vibey gates` lists them."
            )
        return [*lines, "", summary]

    def projects_json(
        self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]
    ) -> str:
        return json.dumps([self._record(project, open_gates) for project in projects], indent=2)

    def _row(self, project: ProjectRecord, open_gates: Mapping[UUID, int]) -> tuple[str, ...]:
        return (
            project.name,
            self._phase(project.phase),
            f"{project.cycle}/{project.max_cycles}",
            str(open_gates.get(project.project_id, 0)),
            project.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M"),
            str(project.project_id),
        )

    def _record(self, project: ProjectRecord, open_gates: Mapping[UUID, int]) -> dict[str, object]:
        return {
            "project_id": str(project.project_id),
            "name": project.name,
            "phase": self._phase(project.phase),
            "cycle": project.cycle,
            "max_cycles": project.max_cycles,
            "repo_path": str(project.repo_path),
            "created_at": project.created_at.isoformat(),
            "open_gates": open_gates.get(project.project_id, 0),
        }

    @staticmethod
    def _phase(phase: StoredPhase) -> str:
        """The phase as the operator reads it: a member's name, or -- for a phase a newer
        vibey wrote (vibey#287) -- its stored text, never a crash."""
        return phase.name if isinstance(phase, Phase) else phase.value


PROJECTS_PRESENTER: Final[ProjectsPresenterInterface] = ProjectsPresenter()


class ProjectsCommand:
    """Reads every project and every open gate, counts the gates per project, prints."""

    def __init__(
        self,
        *,
        presenter: ProjectsPresenterInterface = PROJECTS_PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._open_app = open_app

    async def run(self, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            projects = await resources.projects.list_all()
            gates = await resources.gates.open_all()
        open_gates = Counter(gate.project_id for gate in gates)
        if as_json:
            typer.echo(self._presenter.projects_json(projects, open_gates))
        else:
            typer.echo("\n".join(self._presenter.projects(projects, open_gates)))


PROJECTS: Final[ProjectsCommandInterface] = ProjectsCommand()
"""The command `vibey projects` runs. Annotated with the interface so `mypy --strict` checks
the class against its declared seam."""
