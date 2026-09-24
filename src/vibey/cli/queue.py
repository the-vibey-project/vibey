# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey queue`: see the queue in claim order, and move a job to the front (ADR-0054).

`bump` puts a job next in line -- after whatever is running, which is never
interrupted -- behind every job bumped before it and ahead of everything else, and
pulls its unfinished dependencies forward with it. `unbump` returns it to normal
order. `list` shows what will run, in the order it will run.

Whoever runs this command is the operator. `--source NAME` lets a declared
automation name itself instead; a name `[queue.priority] sources` does not declare is
refused, the refusal is recorded on the ledger, and the command exits non-zero with
the reason (12.j). The human reading comes first; `--json` is the same result for a
program, second (doctrine 7).
"""

import asyncio
import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.dto import QueueEntry
from vibey.application.interfaces import QueuePriorityServiceInterface
from vibey.application.queue_priority import QueuePriorityService
from vibey.bootstrap import AppResources, build_app
from vibey.cli.errors import guard
from vibey.cli.interfaces.queue_interface import QueueCommandInterface, QueuePresenterInterface
from vibey.domain.interfaces.queue_priority_interface import PriorityChangeInterface
from vibey.domain.job import JobState
from vibey.domain.queue_priority import OPERATOR_SOURCE, PriorityAction, PriorityGrant
from vibey.infrastructure.config_loader import QUEUE_CONFIG
from vibey.infrastructure.interfaces import QueueConfigLoaderInterface

DEFAULT_CONFIG: Final = Path("vibey.toml")
"""Where the grant is declared unless `--config` says otherwise: the current
directory's vibey.toml, the file `vibey doctor` reads too."""


class QueuePresenter:
    """Renders the queue and changes to it as lines for a person, or as JSON."""

    def entries(self, entries: Sequence[QueueEntry]) -> list[str]:
        if not entries:
            return ["the queue is empty: nothing is running or waiting"]
        lines: list[str] = []
        position = 0
        for entry in entries:
            job = entry.job
            if job.state is JobState.LEASED:
                place = "running"
            else:
                position += 1
                place = str(position)
            mark = f"bumped #{job.bump_seq}" if job.bump_seq is not None else ""
            item = f" {job.work_item_id}" if job.work_item_id is not None else ""
            waits = ""
            if entry.waiting_on:
                count = len(entry.waiting_on)
                waits = f"  (waits on {count} job{'' if count == 1 else 's'})"
            lines.append(
                f"{place:>7}  {mark:<12} {job.state.value:<17} {job.kind} "
                f"[{job.phase.value}] {job.id}{item}{waits}"
            )
        bumped = sum(1 for entry in entries if entry.job.bump_seq is not None)
        lines.append(
            f"{len(entries)} unfinished job{'' if len(entries) == 1 else 's'}, "
            f"{bumped} bumped; the claim takes waiting work top to bottom"
        )
        return lines

    def entries_json(self, project_id: UUID, entries: Sequence[QueueEntry]) -> str:
        position = 0
        jobs: list[dict[str, object]] = []
        for entry in entries:
            job = entry.job
            place: int | None = None
            if job.state is not JobState.LEASED:
                position += 1
                place = position
            jobs.append(
                {
                    "position": place,
                    "job_id": str(job.id),
                    "state": job.state.value,
                    "kind": job.kind,
                    "phase": job.phase.value,
                    "work_item_id": job.work_item_id,
                    "bump_seq": job.bump_seq,
                    "priority": job.priority,
                    "run_after": job.run_after.isoformat(),
                    "waiting_on": [str(dep) for dep in entry.waiting_on],
                }
            )
        return json.dumps({"project_id": str(project_id), "jobs": jobs}, indent=2)

    def change(self, change: PriorityChangeInterface) -> list[str]:
        verb = "un-bumped" if change.action is PriorityAction.UNBUMP else "bumped"
        if not change.changed:
            state = (
                "is not bumped" if change.action is PriorityAction.UNBUMP else "is already bumped"
            )
            return [f"job {change.target} {state}; nothing moved"]
        lines = [f"{verb} job {change.target} (source: {change.source})"]
        for moved in change.moved:
            place = f"#{moved.bump_seq}" if moved.bump_seq is not None else f"was #{moved.previous}"
            lines.append(f"  moved    {place:<9} {moved.job_id}")
        for kept in change.kept:
            lines.append(f"  ahead    {'':<9} {kept}  (already bumped; keeps its place)")
        for blocked in change.blocked_by:
            lines.append(
                f"  waits on {'':<9} {blocked}  (cannot run and cannot be moved: "
                "the job will not run until someone resolves it)"
            )
        return lines

    def change_json(self, change: PriorityChangeInterface) -> str:
        return json.dumps(
            {
                "action": change.action.value,
                "source": change.source,
                "target": str(change.target),
                "changed": change.changed,
                "moved": [
                    {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": m.previous}
                    for m in change.moved
                ],
                "kept": [str(job_id) for job_id in change.kept],
                "blocked_by": [str(job_id) for job_id in change.blocked_by],
            },
            indent=2,
        )


QUEUE_PRESENTER: Final[QueuePresenterInterface] = QueuePresenter()


class QueueCommand:
    """Reads the grant, opens the app, has the service move or list, prints."""

    def __init__(
        self,
        *,
        presenter: QueuePresenterInterface = QUEUE_PRESENTER,
        config: QueueConfigLoaderInterface = QUEUE_CONFIG,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._config = config
        self._open_app = open_app

    def service(self, resources: AppResources, config: Path) -> QueuePriorityServiceInterface:
        grant = PriorityGrant(self._config.load(config).priority.sources)
        return QueuePriorityService(
            jobs=resources.jobs, store=resources.job_priority, grant=grant, clock=resources.clock
        )

    async def bump(self, job_id: UUID, *, source: str, config: Path, as_json: bool) -> None:
        async with self._open_app() as resources:
            change = await self.service(resources, config).bump(job_id, source=source)
        self._print_change(change, as_json=as_json)

    async def unbump(self, job_id: UUID, *, source: str, config: Path, as_json: bool) -> None:
        async with self._open_app() as resources:
            change = await self.service(resources, config).unbump(job_id, source=source)
        self._print_change(change, as_json=as_json)

    async def list(self, project_id: UUID | None, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            entries = await resources.job_priority.queue(target)
        if as_json:
            typer.echo(self._presenter.entries_json(target, entries))
        else:
            typer.echo("\n".join(self._presenter.entries(entries)))

    def _print_change(self, change: PriorityChangeInterface, *, as_json: bool) -> None:
        if as_json:
            typer.echo(self._presenter.change_json(change))
        else:
            typer.echo("\n".join(self._presenter.change(change)))

    @staticmethod
    async def _project(resources: AppResources, project_id: UUID | None) -> UUID:
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


QUEUE: Final[QueueCommandInterface] = QueueCommand()
"""The command `vibey queue` runs. Annotated with the interface so `mypy --strict`
checks the class against its declared seam."""

queue_app = typer.Typer(name="queue", invoke_without_command=True)

SourceOption = Annotated[
    str,
    typer.Option(
        "--source",
        help="Who is asking. Defaults to the operator, who needs no declaration; any "
        "other name must be declared in `[queue.priority] sources`, or the request is "
        "refused and the refusal recorded on the ledger.",
    ),
]
ConfigOption = Annotated[
    Path,
    typer.Option("--config", help="The vibey.toml that declares `[queue.priority] sources`."),
]
JsonOption = Annotated[bool, typer.Option("--json", help="Print JSON instead of lines.")]


@queue_app.callback(invoke_without_command=True)
def queue(ctx: typer.Context) -> None:
    """See the job queue in claim order, and move a job to the front of it."""
    # Module-level functions from here down because typer builds a command from a
    # plain function's signature. They hold no logic; the command class does.
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@queue_app.command("bump")
def queue_bump(
    job_id: Annotated[UUID, typer.Argument(help="The job to run next.")],
    source: SourceOption = OPERATOR_SOURCE,
    config: ConfigOption = DEFAULT_CONFIG,
    as_json: JsonOption = False,
) -> None:
    """Run a job next: after whatever is running, ahead of all un-bumped work, behind
    anything bumped before it. Its unfinished dependencies move forward with it."""
    with guard():
        asyncio.run(QUEUE.bump(job_id, source=source, config=config, as_json=as_json))


@queue_app.command("unbump")
def queue_unbump(
    job_id: Annotated[UUID, typer.Argument(help="The job to return to normal order.")],
    source: SourceOption = OPERATOR_SOURCE,
    config: ConfigOption = DEFAULT_CONFIG,
    as_json: JsonOption = False,
) -> None:
    """Return a bumped job to normal order, and every bumped job that depends on it."""
    with guard():
        asyncio.run(QUEUE.unbump(job_id, source=source, config=config, as_json=as_json))


@queue_app.command("list")
def queue_list(
    project_id: Annotated[
        UUID | None, typer.Argument(help="Project whose queue to show; defaults to the latest.")
    ] = None,
    as_json: JsonOption = False,
) -> None:
    """Show every unfinished job: running work first, then waiting work in claim order."""
    with guard():
        asyncio.run(QUEUE.list(project_id, as_json=as_json))
