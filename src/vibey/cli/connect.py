# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey connect`: register vibey with frontier chat and IDE clients (ADR-0100, SP-ACP).

Follows the REA-style workflow:
1. Build and display the registration plan (`create`, `update` with `.vibey.bak` backup, or
   `unchanged`), with the protocol each client speaks: `vibey mcp` for the MCP clients,
   `vibey acp` for Zed (an external agent server).
2. When `--dry-run` is given, stop after printing the plan.
3. Require `--yes` or an interactive confirmation before touching any file.
4. Back up existing files and merge the `vibey` entry idempotently.
5. Report every LLM-facing surface of the clients planned (`cli/llm_tooling.py`): the entries it
   just wrote, and the skill and plugin each client installs with its own command, which is
   named.

A client whose file vibey will not rewrite -- one that is not strict JSON, like a Zed settings
file with comments -- is refused with the exact snippet to paste, and the others still go on;
the command then exits 1. Every entry runs the running install's own `vibey`
(`bootstrap.running_vibey`), never one found on `PATH`, as `vibey acp`'s connect step does.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Annotated, Final

import typer

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.bootstrap import running_vibey
from vibey.cli.errors import EXIT_USAGE
from vibey.cli.interfaces.connect_interface import ConnectCommandInterface
from vibey.cli.interfaces.llm_tooling_interface import LlmToolingSectionInterface
from vibey.cli.llm_tooling import LLM_TOOLING_SECTION
from vibey.domain.host_clients import (
    HOST_CLIENT_CATALOG,
    ConnectPlanItem,
    HostClientError,
    HostClientSpec,
)
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface
from vibey.infrastructure.mcp.host_installer import HostInstaller
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface

PROTOCOL_TITLES: Final = {"mcp": "MCP server command", "acp": "ACP agent command"}
REFUSAL_CHARS: Final = 2000
"""Long enough for a refusal's snippet to be printed whole."""


class ConnectCommand:
    """Registers vibey in Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI and Zed.

    Declared by `interfaces/connect_interface.py::ConnectCommandInterface`.
    """

    def __init__(
        self,
        *,
        catalog: HostClientsInterface = HOST_CLIENT_CATALOG,
        installer: HostInstallerInterface | None = None,
        confirm: Callable[[str], bool] = typer.confirm,
        tooling: LlmToolingSectionInterface | None = None,
    ) -> None:
        self._catalog = catalog
        self._installer = installer if installer is not None else PINNED_INSTALLER
        self._confirm = confirm
        self._tooling = tooling

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
                    f"{spec.client_id:<16} {spec.label:<16} ({spec.scope}, {spec.protocol}) "
                    f"{spec.description}"
                )
            return

        try:
            specs = self._catalog.resolve_clients(clients)
        except HostClientError as exc:
            typer.echo(f"Error: {exc}", err=True)
            raise typer.Exit(EXIT_USAGE) from exc
        plan, refused = self._plan(specs)

        self._print_plan(plan)
        for spec, _ in refused:
            typer.echo(f"  [refused  ] {spec.client_id:<15} ({spec.protocol})")
        for spec, why in refused:  # before any question, so a "no" still shows the snippet
            typer.echo(f"Error: {spec.client_id} was not connected: {why}", err=True)
        pending = [item for item in plan if item.action != "unchanged"]
        if dry_run or not pending:
            if not pending and not refused:
                typer.echo("All selected clients are already connected.")
            self._finish(specs, refused)
            return

        if not yes and not self._confirm("Apply these configuration changes?"):
            typer.echo("Cancelled; no files were modified.")
            raise typer.Exit(1)

        try:
            self._installer.apply_plan(plan)
        except HostClientError as exc:
            typer.echo(f"Error: {exc}; no files were modified.", err=True)
            raise typer.Exit(1) from exc
        except OSError as exc:
            typer.echo(f"Error: a file could not be written: {self._cleaned(exc)}", err=True)
            raise typer.Exit(1) from exc
        for item in pending:
            backup_note = f" (backed up to {item.backup_path})" if item.backup_path else ""
            typer.echo(f"{item.action}: {item.client.client_id} -> {item.target_path}{backup_note}")
        self._finish(specs, refused)

    def _plan(
        self, specs: Sequence[HostClientSpec]
    ) -> tuple[list[ConnectPlanItem], list[tuple[HostClientSpec, str]]]:
        """Each client planned on its own, so one file vibey will not rewrite -- or cannot read,
        or cannot parse -- never stops the others. Each refusal is one cleaned line."""
        plan: list[ConnectPlanItem] = []
        refused: list[tuple[HostClientSpec, str]] = []
        for spec in specs:
            try:
                plan.extend(self._installer.build_plan([spec.client_id]))
            except (HostClientError, OSError, ValueError, RecursionError) as exc:
                refused.append((spec, self._cleaned(exc)))
        return plan, refused

    @staticmethod
    def _cleaned(exc: BaseException) -> str:
        """vibey's own refusal as it is (it ends with the snippet to paste); anything else as
        its type and first line. One line either way, with no control character."""
        said = str(exc) if isinstance(exc, HostClientError) else f"{type(exc).__name__}: {exc}"
        return DoctorChecks.cleaned(said, limit=REFUSAL_CHARS)

    def _finish(
        self,
        specs: Sequence[HostClientSpec],
        refused: Sequence[tuple[HostClientSpec, str]],
    ) -> None:
        if self._tooling is not None:
            typer.echo("LLM tooling:")
            for line in self._tooling.lines([spec.client_id for spec in specs]):
                typer.echo(line)
        if refused:
            raise typer.Exit(1)

    @staticmethod
    def _print_plan(plan: Sequence[ConnectPlanItem]) -> None:
        shown: set[str] = set()
        for item in plan:
            if item.client.protocol not in shown:
                shown.add(item.client.protocol)
                title = PROTOCOL_TITLES[item.client.protocol]
                typer.echo(f"{title}: {item.launch.display()}")
        for item in plan:
            backup = f" (backup: {item.backup_path})" if item.backup_path else ""
            typer.echo(
                f"  [{item.action:<9}] {item.client.client_id:<15} ({item.client.protocol}) "
                f"{item.target_path}{backup}"
            )


PINNED_INSTALLER: Final[HostInstallerInterface] = HostInstaller(which=lambda _name: running_vibey())
"""The installer `vibey connect` writes with: every entry runs the running install's own
`vibey` (the console script beside its Python), or this Python, never one found on `PATH`."""
CONNECT_COMMAND: Final[ConnectCommandInterface] = ConnectCommand(tooling=LLM_TOOLING_SECTION)


def connect(
    client: Annotated[
        list[str] | None,
        typer.Option(
            "--client",
            "-c",
            help="Client id to configure (claude_code, claude_desktop, codex, cursor, vscode, "
            "gemini_cli, zed). Repeat for multiple; omit to configure all.",
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
    """Plug vibey into Claude Code, Codex, Claude Desktop, Cursor, VS Code, Gemini CLI or Zed."""
    # Module-level function because Typer builds the command from a plain function signature.
    CONNECT_COMMAND.run(clients=client, yes=yes, dry_run=dry_run, list_clients=list_clients)
