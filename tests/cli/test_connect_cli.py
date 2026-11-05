# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for `vibey connect` CLI and `HostInstaller` (ADR-0100)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibey.cli.connect import CONNECT_COMMAND, ConnectCommand
from vibey.cli.interfaces.connect_interface import ConnectCommandInterface
from vibey.cli.main import app
from vibey.infrastructure.mcp.host_installer import HOST_INSTALLER, HostInstaller
from vibey.infrastructure.mcp.interfaces.host_installer_interface import HostInstallerInterface

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


def test_interfaces_are_satisfied() -> None:
    assert isinstance(HOST_INSTALLER, HostInstallerInterface)
    assert isinstance(CONNECT_COMMAND, ConnectCommandInterface)


def test_connect_list_prints_every_client(capsys: pytest.CaptureFixture[str]) -> None:
    result = runner.invoke(app, ["connect", "--list"])
    assert result.exit_code == 0, result.output
    for client_id in (
        "claude_code",
        "claude_desktop",
        "codex",
        "cursor",
        "vscode",
        "gemini_cli",
    ):
        assert client_id in result.stdout


def test_connect_dry_run_apply_backup_and_idempotency(tmp_path: Path) -> None:
    home = tmp_path / "home"
    proj = tmp_path / "proj"
    home.mkdir()
    proj.mkdir()

    # Pre-populate .mcp.json so we exercise the update + backup path
    mcp_json = proj / ".mcp.json"
    mcp_json.write_text('{"mcpServers": {"existing": {"command": "echo"}}}\n')

    installer = HostInstaller(
        home_dir=lambda: home,
        project_dir=lambda: proj,
        platform="darwin",
        which=lambda _: "/opt/homebrew/bin/vibey",
        python_executable="/usr/bin/python3",
    )
    cmd = ConnectCommand(installer=installer, confirm=lambda _: True)

    # 1. Dry run writes nothing
    cmd.run(clients=["claude_code", "codex"], yes=False, dry_run=True, list_clients=False)
    assert not (home / ".codex" / "config.toml").exists()
    assert not (proj / ".mcp.json.vibey.bak").exists()

    # 2. User declines confirmation -> exits 1 and writes nothing
    declining = ConnectCommand(installer=installer, confirm=lambda _: False)
    with pytest.raises(Exception) as declined:
        declining.run(clients=["codex"], yes=False, dry_run=False, list_clients=False)
    assert getattr(declined.value, "exit_code", None) == 1
    assert not (home / ".codex" / "config.toml").exists()

    # 3. Apply with --yes creates codex config and updates .mcp.json with backup
    cmd.run(clients=["claude_code", "codex"], yes=True, dry_run=False, list_clients=False)
    assert (proj / ".mcp.json.vibey.bak").exists()
    assert "existing" in (proj / ".mcp.json.vibey.bak").read_text()
    merged = json.loads(mcp_json.read_text())
    assert merged["mcpServers"]["existing"] == {"command": "echo"}
    assert merged["mcpServers"]["vibey"] == {
        "command": "/opt/homebrew/bin/vibey",
        "args": ["mcp"],
    }
    codex_toml = (home / ".codex" / "config.toml").read_text()
    assert "[mcp_servers.vibey]" in codex_toml

    # 4. Re-running reports all selected clients already connected (unchanged branch in apply_plan)
    plan = installer.build_plan(["claude_code", "codex"])
    assert all(item.action == "unchanged" for item in plan)
    installer.apply_plan(plan)
    cmd.run(clients=["claude_code", "codex"], yes=True, dry_run=False, list_clients=False)


def test_connect_rejects_unknown_client_with_exit_2() -> None:
    result = runner.invoke(app, ["connect", "--client", "nope"])
    assert result.exit_code == 2
    assert "unknown client 'nope'" in result.output
