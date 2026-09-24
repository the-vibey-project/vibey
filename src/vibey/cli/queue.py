# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey queue`: see the queue in claim order, and move a job to the front (ADR-0054).

`bump` puts a job next in line -- after whatever is running, which is never interrupted
-- behind every job bumped before it and ahead of everything else, and pulls its
unfinished dependencies forward with it. `unbump` takes it out of the named set; the lane
is re-derived, so nothing it pulled in is left behind unless another named job needs it.
`list` shows what will run, in the order it will run.

Who may reorder is decided by the project's own reviewed configuration, never by
anything on this command line: the operator is the account that owns
`<repo>/vibey.toml`, and `--source NAME` is honoured only for a name that file declares,
run by that same account. Anyone else is refused, the refusal is recorded, and the
command exits 3 with the reason (12.j). Every request is recorded on the ledger.
The human reading comes first; `--json` is the same result for a program (doctrine 7).
"""

import asyncio
import json
from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.dto import JobRecord, QueueEntry
from vibey.bootstrap import AppResources, build_app
from vibey.cli.errors import guard
from vibey.cli.interfaces.queue_interface import QueueCommandInterface, QueuePresenterInterface
from vibey.domain.interfaces.queue_priority_interface import PriorityChangeInterface
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import PriorityAction


class QueuePresenter:
    """Renders the queue and changes to it as lines for a person, or as JSON."""

    def entries(self, entries: Sequence[QueueEntry]) -> list[str]:
        if not entries:
            return ["the queue is empty: nothing is running or waiting"]
        lines: list[str] = []
        position = 0
        for entry in entries:
            job = entry.job
            held = self._unclaimable(job)
            if held:
                place = "-"
            elif job.state is JobState.LEASED:
                place = "running"
            else:
                position += 1
                place = str(position)
            mark = f"bumped #{job.bump_seq}" if job.bump_seq is not None else ""
            item = f" {job.work_item_id}" if job.work_item_id is not None else ""
            pulled = ""
            if job.bump_seq is not None and not job.bump_named:
                pulled = "  (pulled in as a bumped job's dependency)"
            waits = ""
            if entry.waiting_on:
                count = len(entry.waiting_on)
                waits = f"  (waits on {count} job{'' if count == 1 else 's'})"
            lines.append(
                f"{place:>7}  {mark:<12} {job.state.value:<17} {job.kind} "
                f"[{job.phase.value}] {job.id}{item}{pulled}{waits}{held}"
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
            claimable = not self._unclaimable(job)
            if claimable and job.state is not JobState.LEASED:
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
                    "bump_named": job.bump_named,
                    "priority": job.priority,
                    "run_after": job.run_after.isoformat(),
                    "waiting_on": [str(dep) for dep in entry.waiting_on],
                    "claimable_here": claimable,
                }
            )
        return json.dumps({"project_id": str(project_id), "jobs": jobs}, indent=2)

    @staticmethod
    def _unclaimable(job: JobRecord) -> str:
        """Why no worker of this release will ever claim `job` -- a phase or a state a
        newer vibey wrote (vibey#287) -- or "" when one can. Such a row is shown, never
        given a place in a line it will not be taken from."""
        if not isinstance(job.phase, Phase):
            return f"  (not claimable by this vibey: phase {job.phase.value!r} is unknown)"
        if not isinstance(job.state, JobState):
            return f"  (not claimable by this vibey: state {job.state.value!r} is unknown)"
        return ""

    def change(self, change: PriorityChangeInterface) -> list[str]:
        if not change.changed:
            return [f"job {change.target}: {change.note} (recorded; by {change.requested_by})"]
        verb = "un-bumped" if change.action is PriorityAction.UNBUMP else "bumped"
        lines = [f"{verb} job {change.target} (by {change.requested_by})"]
        if change.named:
            lines.append(
                "  it was already bumped for another job; it keeps its place and is now "
                "bumped by name"
            )
        for moved in change.moved:
            place = f"#{moved.bump_seq}" if moved.bump_seq is not None else f"was #{moved.previous}"
            lines.append(f"  moved    {place:<9} {moved.job_id}")
        for kept in change.kept:
            lines.append(f"  ahead    {'':<9} {kept}  (already bumped; keeps its place)")
        return lines

    def change_json(self, change: PriorityChangeInterface) -> str:
        return json.dumps(
            {
                "action": change.action.value,
                "by": change.requested_by,
                "target": str(change.target),
                "changed": change.changed,
                "named": change.named,
                "note": change.note,
                "moved": [
                    {"job_id": str(m.job_id), "bump_seq": m.bump_seq, "previous": m.previous}
                    for m in change.moved
                ],
                "kept": [str(job_id) for job_id in change.kept],
            },
            indent=2,
        )


QUEUE_PRESENTER: Final[QueuePresenterInterface] = QueuePresenter()


class QueueCommand:
    """Opens the app, asks the one priority service to move or list, prints."""

    def __init__(
        self,
        *,
        presenter: QueuePresenterInterface = QUEUE_PRESENTER,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._open_app = open_app

    async def bump(
        self, job_id: UUID, *, project_id: UUID | None, source: str | None, as_json: bool
    ) -> None:
        async with self._open_app() as resources:
            project = await self._project(resources, project_id)
            change = await resources.queue_priority.bump(project, job_id, source=source)
        self._print_change(change, as_json=as_json)

    async def unbump(
        self, job_id: UUID, *, project_id: UUID | None, source: str | None, as_json: bool
    ) -> None:
        async with self._open_app() as resources:
            project = await self._project(resources, project_id)
            change = await resources.queue_priority.unbump(project, job_id, source=source)
        self._print_change(change, as_json=as_json)

    async def list(self, project_id: UUID | None, *, as_json: bool) -> None:
        async with self._open_app() as resources:
            target = await self._project(resources, project_id)
            entries = await resources.queue_priority.queue(target)
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

ProjectOption = Annotated[
    UUID | None,
    typer.Option(
        "--project",
        help="The project whose queue this is; defaults to the latest. The grant is read "
        "from this project's own vibey.toml, and the request is recorded on its ledger.",
    ),
]
SourceOption = Annotated[
    str | None,
    typer.Option(
        "--source",
        help="An automation naming itself. Omitted, the caller must be the operator: the "
        "account that owns the project's vibey.toml. Given, the name must be declared in "
        "that file's `[queue.priority] sources` and the caller must still be that account. "
        "Anything else is refused and the refusal recorded.",
    ),
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
    project_id: ProjectOption = None,
    source: SourceOption = None,
    as_json: JsonOption = False,
) -> None:
    """Run a job next: after whatever is running, ahead of all un-bumped work, behind
    anything bumped before it. Its unfinished dependencies move forward with it."""
    with guard():
        asyncio.run(QUEUE.bump(job_id, project_id=project_id, source=source, as_json=as_json))


@queue_app.command("unbump")
def queue_unbump(
    job_id: Annotated[UUID, typer.Argument(help="The job to return to normal order.")],
    project_id: ProjectOption = None,
    source: SourceOption = None,
    as_json: JsonOption = False,
) -> None:
    """Take a job out of the lane, with every pulled-in dependency no remaining named job
    needs. Refused while another named job depends on this one."""
    with guard():
        asyncio.run(QUEUE.unbump(job_id, project_id=project_id, source=source, as_json=as_json))


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
