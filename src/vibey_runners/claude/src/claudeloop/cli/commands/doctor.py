# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

from pathlib import Path

import typer

from claudeloop import bootstrap
from claudeloop.application.usecases.doctor import all_passed, run_doctor
from claudeloop.cli.render import render_doctor_checks
from claudeloop.infrastructure.config import load_config

app = typer.Typer(add_completion=False)


@app.callback(invoke_without_command=True)
def doctor(
    ctx: typer.Context,
    profile: str | None = typer.Option(
        None,
        "--profile",
        help="Check this backend profile ([profiles.NAME]) instead of Anthropic",
    ),
) -> None:
    """Pre-flight checks before starting a long unattended run: Claude Code
    installed and authenticated, configured MCP servers, working-directory
    safety — and, for a local backend profile, that it answers, has every model
    the profile names, and that those models make real tool calls. Run this BEFORE `run`/`resume`, not instead of them."""
    if ctx.invoked_subcommand is not None:
        return
    cwd = Path.cwd()
    try:
        config = load_config(cwd=cwd, cli_overrides={"profile": profile})
    except ValueError as exc:
        typer.echo(f"Invalid configuration: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    env = bootstrap.build_doctor_environment()
    resolver = bootstrap.build_backend_resolver()
    checks = run_doctor(
        env,
        cwd=cwd,
        backend=config.backend,
        auth_token=resolver.try_auth_token(config.backend),
    )
    typer.echo(render_doctor_checks(checks))
    if not all_passed(checks):
        raise typer.Exit(code=1)
