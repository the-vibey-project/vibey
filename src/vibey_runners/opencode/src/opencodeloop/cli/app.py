# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""CLI composition root for the OpenCode runner."""

import uuid
from pathlib import Path
from typing import Annotated

import typer

from opencodeloop import __version__
from opencodeloop.application.interfaces import RunnerInterface
from opencodeloop.application.runner import OpencodeRunner
from opencodeloop.infrastructure.interfaces import FileRunStoreInterface, OpenCodeProcessInterface
from opencodeloop.infrastructure.opencode_process import OpenCodeProcess
from opencodeloop.infrastructure.run_store import FileRunStore

app = typer.Typer(name="opencodeloop", no_args_is_help=True, add_completion=False)
RESUME_PROMPT = "Continue the assigned work from this session and complete any remaining work."


def _runner() -> RunnerInterface:
    """Compose CLI commands from the only concrete process and store adapters."""
    process: OpenCodeProcessInterface = OpenCodeProcess()
    store: FileRunStoreInterface = FileRunStore()
    return OpencodeRunner(process, store)


def _version(value: bool) -> None:
    """Typer's eager callback is required to provide the shared `--version` contract."""
    if value:
        typer.echo(f"opencodeloop {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True)] = False,
) -> None:
    """Run OpenCode through Vibey's normalized process contract."""
    del version


@app.command()
def doctor() -> None:
    """Check the installed OpenCode CLI and its JSON event interface."""
    ready, detail = _runner().doctor()
    typer.echo(detail)
    if not ready:
        raise typer.Exit(code=1)


@app.command()
def run(
    plan: Annotated[Path, typer.Argument(help="Plan file to send to OpenCode.")],
    run_id: Annotated[str, typer.Option("--run-id")] = "",
    cwd: Annotated[Path, typer.Option("--cwd")] = Path("."),
) -> None:
    """Execute one plan and persist normalized events in the worktree."""
    prompt = plan.read_text(encoding="utf-8")
    resolved_run_id = run_id or str(uuid.uuid4())
    try:
        result = _runner().run(prompt=prompt, run_id=resolved_run_id, cwd=cwd.resolve())
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    if result.detail:
        typer.echo(result.detail, err=True)
    raise typer.Exit(code=0 if result.succeeded else 1)


@app.command()
def resume(
    session_id: Annotated[str, typer.Argument(help="OpenCode session identifier.")],
    run_id: Annotated[str, typer.Option("--run-id")] = "",
    cwd: Annotated[Path, typer.Option("--cwd")] = Path("."),
    prompt: Annotated[str, typer.Option("--prompt")] = RESUME_PROMPT,
) -> None:
    """Resume a provider session when OpenCode exposes one."""
    try:
        result = _runner().run(
            prompt=prompt,
            run_id=run_id or session_id,
            cwd=cwd.resolve(),
            session_id=session_id,
        )
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from exc
    if result.detail:
        typer.echo(result.detail, err=True)
    raise typer.Exit(code=0 if result.succeeded else 1)


def main() -> None:
    """Console-script entry point."""
    app()
