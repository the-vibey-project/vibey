# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey abandon PROJECT_ID --reason TEXT`: the operator's clean exit for a project that
is not going to finish.

The project moves into abandoned through the phase machine's own guard, every job of it
that could still run is cancelled, and every gate it is waiting on is withdrawn -- in one
transaction, recorded on its ledger as a `PhaseTransitioned` carrying the reason, who
abandoned it and what it stopped, and one `GateWithdrawn` per gate. Nothing is deleted.
Abandoning a project already abandoned changes nothing and says so; a done project is
refused, since it finished. `--dry-run` lists what would be cancelled and withdrawn and
writes nothing.

The human reading is one short block; `--json` is the same report for a program -- a
fixed contract (doctrine 7).
"""

import asyncio
import json
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Annotated, Final
from uuid import UUID

import typer

from vibey.application.dto import AbandonmentReport
from vibey.bootstrap import AppResources, build_app
from vibey.cli.errors import guard
from vibey.cli.interfaces.abandon_interface import (
    AbandonCommandInterface,
    AbandonPresenterInterface,
)
from vibey.domain.abandonment import ABANDONMENT_POLICY
from vibey.domain.errors import InvalidAbandonment
from vibey.domain.interfaces.abandonment_interface import AbandonmentPolicyInterface
from vibey.domain.phase import Phase


class AbandonPresenter:
    """Renders an abandonment as a short plain block, or as the JSON contract."""

    def report(self, report: AbandonmentReport, *, dry_run: bool) -> list[str]:
        project = report.project
        named = f"{project.name} ({project.project_id})"
        if report.already_abandoned:
            change = "nothing would change" if dry_run else "nothing was changed"
            return [f"{named} is already abandoned; {change}."]
        lines = ["Dry run: nothing was written."] if dry_run else []
        verb = "Would abandon" if dry_run else "Abandoned"
        lines.append(
            f"{verb} {named}: {report.left.value} -> {Phase.ABANDONED.value}, "
            f"cycle {project.cycle}."
        )
        lines.append(f"  by {report.by} (account {report.account})")
        lines.append(f"  reason: {report.reason}")
        cancel = "would cancel" if dry_run else "cancelled"
        lines.append(f"  {cancel} {self._count(len(report.jobs), 'job')}")
        lines.extend(f"    {job.id} {job.kind} (was {job.state.value})" for job in report.jobs)
        withdraw = "would withdraw" if dry_run else "withdrew"
        lines.append(f"  {withdraw} {self._count(len(report.gates), 'gate')}")
        lines.extend(f"    {gate.gate_id} {gate.kind}" for gate in report.gates)
        return lines

    def document(self, report: AbandonmentReport, *, dry_run: bool) -> dict[str, object]:
        project = report.project
        return {
            "project_id": str(project.project_id),
            "name": project.name,
            "from": report.left.value,
            "to": Phase.ABANDONED.value,
            "cycle": project.cycle,
            "dry_run": dry_run,
            "already_abandoned": report.already_abandoned,
            "written": report.written,
            "reason": report.reason,
            "by": report.by,
            "account": report.account,
            "cancelled_jobs": [
                {"job_id": str(job.id), "kind": job.kind, "state": job.state.value}
                for job in report.jobs
            ],
            "withdrawn_gates": [
                {
                    "gate_id": str(gate.gate_id),
                    "kind": gate.kind,
                    "job_id": str(gate.job_id) if gate.job_id is not None else None,
                }
                for gate in report.gates
            ],
        }

    def report_json(self, report: AbandonmentReport, *, dry_run: bool) -> str:
        return json.dumps(self.document(report, dry_run=dry_run), indent=2)

    @staticmethod
    def _count(count: int, noun: str) -> str:
        listed = ":" if count else ""
        return f"{count} {noun}{'' if count == 1 else 's'}{listed}"


ABANDON_PRESENTER: Final[AbandonPresenterInterface] = AbandonPresenter()


class AbandonCommand:
    """Checks what it can before touching the database, opens the app, asks the one
    abandonment service, prints."""

    def __init__(
        self,
        *,
        presenter: AbandonPresenterInterface = ABANDON_PRESENTER,
        policy: AbandonmentPolicyInterface = ABANDONMENT_POLICY,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
    ) -> None:
        self._presenter = presenter
        self._policy = policy
        self._open_app = open_app

    async def run(
        self,
        project_id: UUID,
        *,
        reason: str,
        by: str | None,
        as_json: bool,
        dry_run: bool,
    ) -> None:
        self._usage(lambda: self._policy.reason(reason), "--reason")
        self._usage(lambda: self._policy.actor(by, account=""), "--by")
        async with self._open_app() as resources:
            # The resolution and exit code every project-scoped command gives for an id
            # that names nothing (`vibey budget`, `vibey cost`): exit 1, said plainly.
            if await resources.projects.get(project_id) is None:
                typer.echo(f"unknown project {project_id}")
                raise typer.Exit(1)
            service = resources.project_abandonment
            act = service.preview if dry_run else service.abandon
            report = await act(project_id, reason=reason, by=by)
        typer.echo(
            self._presenter.report_json(report, dry_run=dry_run)
            if as_json
            else "\n".join(self._presenter.report(report, dry_run=dry_run))
        )

    @staticmethod
    def _usage(check: Callable[[], object], hint: str) -> None:
        """A request vibey would refuse is a usage error (exit 2), found before anything
        is opened, rather than a refusal (exit 3) found after."""
        try:
            check()
        except InvalidAbandonment as exc:
            raise typer.BadParameter(str(exc), param_hint=hint) from exc


ABANDON: Final[AbandonCommandInterface] = AbandonCommand()
"""The command `vibey abandon` runs. Annotated with the interface so `mypy --strict`
checks the class against its declared seam."""


# A module-level function because typer builds a command from a plain function's
# signature. It holds no logic; the command class does.
def abandon(
    project_id: Annotated[UUID, typer.Argument(help="The project to abandon.")],
    reason: Annotated[
        str,
        typer.Option(
            "--reason",
            help="Why the project is being abandoned. Recorded on its ledger with the move.",
        ),
    ],
    by: Annotated[
        str | None,
        typer.Option(
            "--by",
            help="The name this abandonment is recorded under, for a tool that runs the "
            "command. Defaults to the account running it. A label for the record, not a "
            "permission: the account is recorded beside it.",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print JSON instead (project_id, name, from, to, cycle, dry_run, "
            "already_abandoned, written, reason, by, account, cancelled_jobs, "
            "withdrawn_gates).",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="List what would be cancelled and withdrawn; write nothing."
        ),
    ] = False,
) -> None:
    """Abandon a project that is not going to finish: its jobs are cancelled, its gates
    withdrawn, and the move is recorded on its ledger with the reason.

    A project already abandoned is left as it is (exit 0); a done project is refused.
    """
    with guard():
        asyncio.run(ABANDON.run(project_id, reason=reason, by=by, as_json=as_json, dry_run=dry_run))
