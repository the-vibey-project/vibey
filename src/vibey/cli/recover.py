# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey recover --stop-workers`: what it says while it stops this user's workers."""

import typer

from vibey.infrastructure.interfaces.worker_processes_interface import WorkerStopperInterface

_SHOWN_CHARS = 150


def _shown(command: str) -> str:
    return command if len(command) <= _SHOWN_CHARS else command[: _SHOWN_CHARS - 1] + "…"


def stop_workers(stopper: WorkerStopperInterface, *, grace_seconds: float, dry_run: bool) -> bool:
    """Show the `vibey worker` processes this user is running, and stop them unless `dry_run`.

    True when nothing is left running that could still hold a lease, so resetting the leases is
    safe; False when a process survived even SIGKILL, so it is not.
    """
    plan = stopper.plan()
    if not plan.workers:
        typer.echo("no vibey worker processes are running")
        return True
    typer.echo(("would stop" if dry_run else "stopping") + " these processes:")
    for row in plan.workers:
        typer.echo(f"  worker {row.pid}: {_shown(row.command)}")
    for row in plan.descendants:
        typer.echo(f"  started by a worker, {row.pid}: {_shown(row.command)}")
    if dry_run:
        return True
    report = stopper.stop(plan, grace_seconds=grace_seconds)
    typer.echo(f"{len(report.terminated)} stopped on SIGTERM, {len(report.killed)} needed SIGKILL")
    if report.survivors:
        pids = ", ".join(str(pid) for pid in report.survivors)
        typer.echo(
            f"still running after SIGKILL: {pids}. Leases were not reset: a live worker holds "
            "them, and resetting them would run its job twice."
        )
        return False
    return True
