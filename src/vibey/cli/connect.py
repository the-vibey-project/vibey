# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey connect`: register `vibey mcp` with frontier chat and IDE clients (ADR-0100).

Follows the REA-style workflow:
1. Build and display the registration plan (`create`, `update` with `.vibey.bak` backup, or
   `unchanged`).
2. When `--dry-run` is given, stop after printing the plan.
3. Require `--yes` or an interactive confirmation before touching any file.
4. Back up existing files and merge the `vibey` MCP server entry idempotently.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, Final

import typer

from vibey.cli.errors import EXIT_USAGE
from vibey.cli.interfaces.connect_interface import ConnectCommandInterface
from vibey.domain.host_clients import HOST_CLIENT_CATALOG, ConnectPlanItem, HostClientError
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.host_installer import HOST_INSTALLER
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface


class ConnectCommand:
    """Registers `vibey mcp` in Claude Code, Claude Desktop, Codex, Cursor, VS Code and Gemini CLI.

    Declared by `interfaces/connect_interface.py::ConnectCommandInterface`.
    """

    def __init__(
        self,
        *,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        installer: HostInstallerInterface = HOST_INSTALLER,
        confirm: Callable[[str], bool] = typer.confirm,
    ) -> None:
        self._catalog = catalog
        self._installer = installer
        self._confirm = confirm

    def run(
        self,
        *,
        clients: Sequence[str] | None,
        yes: bool,
        dry_run: bool,
        list_clients: bool,
    ) -> None:
        if list_clients:
            for spec in self._catalog.all():
                typer.echo(
                    f"{spec.client_id:<16} {spec.label:<16} ({spec.scope}) {spec.description}"
                )
            return

        try:
            plan = self._installer.build_plan(clients)
        except HostClientError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(EXIT_USAGE) from exc

        self._print_plan(plan)
        pending = [item for item in plan if item.action != "unchanged"]
        if dry_run or not pending:
            if not pending:
                typer.echo("All selected clients are already connected.")
            return

        if not yes and not self._confirm("Apply these MCP configuration changes?"):
            typer.echo("Cancelled; no files were modified.")
            raise typer.Exit(1)

        self._installer.apply_plan(plan)
        for item in pending:
            backup_note = f" (backed up to {item.backup_path})" if item.backup_path else ""
            typer.echo(f"{item.action}: {item.client.client_id} -> {item.target_path}{backup_note}")

    @staticmethod
    def _print_plan(plan: Sequence[ConnectPlanItem]) -> None:
        launch = plan[0].launch.display() if plan else "vibey mcp"
        typer.echo(f"MCP server command: {launch}")
        for item in plan:
            backup = f" (backup: {item.backup_path})" if item.backup_path else ""
            typer.echo(
                f"  [{item.action:<9}] {item.client.client_id:<15} {item.target_path}{backup}"
            )


CONNECT_COMMAND: Final[ConnectCommandInterface] = ConnectCommand()


def connect(
    client: Annotated[
        list[str] | None,
        typer.Option(
            "--client",
            "-c",
            help="Client id to configure (claude_code, claude_desktop, codex, cursor, vscode, "
            "gemini_cli). Repeat for multiple; omit to configure all.",
        ),
    ] = None,
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Apply the plan without interactive confirmation."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show the planned changes and exit without writing files."),
    ] = False,
    list_clients: Annotated[
        bool,
        typer.Option("--list", help="List supported host clients and exit."),
    ] = False,
) -> None:
    """Plug vibey into Claude Code, Codex, Claude Desktop, Cursor, VS Code or Gemini CLI over MCP."""
    # Module-level function because Typer builds the command from a plain function signature.
    CONNECT_COMMAND.run(clients=client, yes=yes, dry_run=dry_run, list_clients=list_clients)
