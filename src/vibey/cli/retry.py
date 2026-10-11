# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey retry PROJECT`: get a stalled project moving again in one command.

A project that stalls on a bad model answer parks its job on an `attempts_exhausted` gate, and
getting it going again was four commands and a restart script: stop the old worker so it holds no
lease, answer the gate with more attempts, start a worker with the right flags, then watch it.
This is that, in order, and nothing else:

1. Stop this user's `vibey worker` processes, as `vibey recover --stop-workers` does (a live
   worker holds its leases; if one survives SIGKILL nothing else is done).
2. Answer each of the project's `attempts_exhausted` gates with a grant of `--max-attempts`. Every
   other gate is a decision, so it is only named, never answered: `vibey gates PROJECT` has them.
3. With `--start-worker`, start `vibey worker --project PROJECT ...` detached, passing along
   everything after `--`, and say where its log is.

Updating vibey itself is not here: after a fix lands, `git pull` and `uv sync` are still yours.
"""

from collections.abc import Callable, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Final
from uuid import UUID

import typer

from vibey.application.worker import ATTEMPTS_GRANT_KEY
from vibey.bootstrap import AppResources, build_app
from vibey.cli.recover import stop_workers
from vibey.domain.job import ATTEMPTS_EXHAUSTED_GATE_KIND
from vibey.infrastructure.interfaces.worker_launcher_interface import WorkerLauncherInterface
from vibey.infrastructure.interfaces.worker_processes_interface import WorkerStopperInterface
from vibey.infrastructure.worker_launcher import (
    WorkerLauncher,
    default_executable,
    default_log,
)
from vibey.infrastructure.worker_processes import WorkerStopper

DEFAULT_MAX_ATTEMPTS: Final[int] = 10
"""The grant `vibey gates` itself suggests for an exhausted job."""


class RetryCommand:
    """Stops workers, grants attempts on exhausted gates, and optionally starts a worker."""

    def __init__(
        self,
        *,
        stopper: WorkerStopperInterface,
        launcher: WorkerLauncherInterface,
        open_app: Callable[[], AbstractAsyncContextManager[AppResources]] = build_app,
        echo: Callable[[str], None] = typer.echo,
    ) -> None:
        self._stopper = stopper
        self._launcher = launcher
        self._open_app = open_app
        self._echo = echo

    async def run(
        self,
        project_id: UUID,
        *,
        max_attempts: int,
        keep_workers: bool,
        start_worker: bool,
        worker_args: Sequence[str],
        log: Path | None,
        grace_seconds: float,
        dry_run: bool,
    ) -> None:
        async with self._open_app() as resources:
            project = await resources.projects.get(project_id)
            if project is None:
                typer.echo(f"unknown project {project_id}", err=True)
                raise typer.Exit(1)
            gates = await resources.gates.open_for_project(project_id)
            exhausted = [gate for gate in gates if gate.kind == ATTEMPTS_EXHAUSTED_GATE_KIND]
            others = len(gates) - len(exhausted)

            if not keep_workers and not stop_workers(
                self._stopper, grace_seconds=grace_seconds, dry_run=dry_run
            ):
                raise typer.Exit(1)

            verb = "would grant" if dry_run else "granting"
            for gate in exhausted:
                self._echo(f"{verb} {max_attempts} attempts on gate {gate.gate_id}")
                if not dry_run:
                    # A named request, so running this twice answers the gate once.
                    await resources.gate_answers.answer(
                        gate.gate_id,
                        {ATTEMPTS_GRANT_KEY: max_attempts},
                        by="vibey retry",
                        request_id=f"retry-{gate.gate_id}-{max_attempts}",
                    )
            if not exhausted:
                self._echo(f"{project.name}: no exhausted-attempts gate is open")
            if others:
                self._echo(f"{others} other open gate(s) need a person: vibey gates {project_id}")

        arguments = [
            "worker",
            *([] if "--project" in worker_args else ["--project", str(project_id)]),
        ]
        arguments += worker_args
        logfile = log if log is not None else default_log(project_id)
        if not start_worker:
            self._echo(
                "no worker started; to start one: vibey retry --start-worker " + str(project_id)
            )
            return
        if dry_run:
            self._echo(f"would start: vibey {' '.join(arguments)} (log {logfile})")
            return
        pid = self._launcher.start(arguments, log=logfile)
        self._echo(f"worker started (pid {pid}); log: {logfile}")
        self._echo("watch it: vibey llm tail")


RETRY: Final = RetryCommand(
    stopper=WorkerStopper(), launcher=WorkerLauncher(executable=default_executable())
)
"""The command `vibey retry` runs."""
