# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey recover --stop-workers`: what it says while it stops this user's workers."""

import typer

from vibey.infrastructure.interfaces.worker_processes_interface import WorkerStopperInterface

_SHOWN_CHARS = 150


def _shown(command: str) -> str:
    return command if len(command) <= _SHOWN_CHARS else command[: _SHOWN_CHARS - 1] + "…"


def stop_workers(
    stopper: WorkerStopperInterface,
    *,
    grace_seconds: float,
    dry_run: bool,
    project_id: str | None = None,
    include_shared: bool = False,
    shared_blocks: bool = False,
) -> bool:
    """Show the `vibey worker` processes this user is running, and stop them unless `dry_run`.

    With `project_id`, only that project's workers. A worker serving every project, or none in
    particular, is left running and named; when `shared_blocks` (a recovery that resets leases)
    it also makes the result False, because it may hold a lease on this project.

    True when nothing is left running that could still hold a lease, so resetting the leases is
    safe; False when a process survived even SIGKILL, or a shared worker was left, so it is not.
    """
    plan = (
        stopper.plan()
        if project_id is None
        else stopper.plan(project_id, include_shared=include_shared)
    )
    if not plan.workers:
        typer.echo(
            "no vibey worker processes are running"
            if project_id is None
            else f"no vibey worker is running for project {project_id}"
        )
    else:
        typer.echo(("would stop" if dry_run else "stopping") + " these processes:")
        for row in plan.workers:
            typer.echo(f"  worker {row.pid}: {_shown(row.command)}")
        for row in plan.descendants:
            typer.echo(f"  started by a worker, {row.pid}: {_shown(row.command)}")
        if not dry_run:
            report = stopper.stop(plan, grace_seconds=grace_seconds)
            typer.echo(
                f"{len(report.terminated)} stopped on SIGTERM, {len(report.killed)} needed SIGKILL"
            )
            if report.survivors:
                pids = ", ".join(str(pid) for pid in report.survivors)
                typer.echo(
                    f"still running after SIGKILL: {pids}. Leases were not reset: a live worker "
                    "holds them, and resetting them would run its job twice."
                )
                return False
    if plan.left_running:
        typer.echo("left running, because it serves more than this project:")
        for row in plan.left_running:
            typer.echo(f"  worker {row.pid}: {_shown(row.command)}")
        if shared_blocks and not dry_run:
            typer.echo(
                "Leases were not reset: a worker that serves every project may hold one of "
                "this project's, and resetting it would run its job twice. Add --include-shared "
                "to stop it too."
            )
            return False
    return True
