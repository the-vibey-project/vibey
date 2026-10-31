# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which project a command acts on when PROJECT_ID is optional (`engines`, `cost`).

With none given it is the newest. The two refusals keep the words and exit code they always
had (exit 1). In text mode they go to stdout, as before; under `--json` they go to stderr, so
stdout is only ever the document (#1686).
"""

from __future__ import annotations

from typing import Final
from uuid import UUID

import typer

from vibey.application.dto import ProjectRecord
from vibey.bootstrap import AppResources
from vibey.cli.interfaces.project_target_interface import ProjectTargetInterface


class ProjectTarget:
    """Implements `ProjectTargetInterface`."""

    async def latest(self, resources: AppResources, *, as_json: bool) -> ProjectRecord:
        project = await resources.projects.get_latest()
        if project is None:
            typer.echo("no projects found; create one with `vibey new` first", err=as_json)
            raise typer.Exit(1)
        return project

    async def get(
        self, resources: AppResources, project_id: UUID, *, as_json: bool
    ) -> ProjectRecord:
        project = await resources.projects.get(project_id)
        if project is None:
            typer.echo(f"unknown project {project_id}", err=as_json)
            raise typer.Exit(1)
        return project


PROJECT_TARGET: Final[ProjectTargetInterface] = ProjectTarget()
