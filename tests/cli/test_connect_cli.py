# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for `vibey connect` CLI and `HostInstaller` (ADR-0100)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
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


def test_connect_refuses_a_config_that_resolves_outside_home(tmp_path: Path) -> None:
    home, outside = tmp_path / "home", tmp_path / "outside"
    (home / ".cursor").mkdir(parents=True)
    outside.mkdir()
    (outside / "mcp.json").write_text("{}")
    (home / ".cursor" / "mcp.json").symlink_to(outside / "mcp.json")
    installer = HostInstaller(
        home_dir=lambda: home, project_dir=lambda: tmp_path, platform="linux", which=lambda _n: None
    )
    command = ConnectCommand(installer=installer)

    with pytest.raises(typer.Exit) as stopped:
        command.run(clients=["cursor"], yes=True, dry_run=False, list_clients=False)

    assert stopped.value.exit_code == 1
    assert (outside / "mcp.json").read_text() == "{}"


# ------------------------------------------------------------------------- Zed over ACP

COMMENTED_ZED = '// Zed settings\n{\n  "theme": "One Dark", // mine\n}\n'


def _installer(tmp_path: Path, *, launcher: str | None = "/opt/vibey/bin/vibey") -> HostInstaller:
    home, proj = tmp_path / "home", tmp_path / "proj"
    home.mkdir(exist_ok=True)
    proj.mkdir(exist_ok=True)
    return HostInstaller(
        home_dir=lambda: home,
        project_dir=lambda: proj,
        platform="darwin",
        which=lambda _: launcher,
        python_executable="/usr/bin/python3",
    )


def test_connect_list_names_zed_as_an_acp_client() -> None:
    result = runner.invoke(app, ["connect", "--list"])
    assert result.exit_code == 0, result.output
    zed = next(line for line in result.stdout.splitlines() if line.startswith("zed "))
    assert "Zed" in zed and "acp" in zed and "agent_servers" in zed
    cursor = next(line for line in result.stdout.splitlines() if line.startswith("cursor "))
    assert "mcp" in cursor


def test_connect_registers_vibey_acp_in_zed_and_shows_each_protocol(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = _installer(tmp_path)
    ConnectCommand(installer=installer).run(
        clients=["zed", "cursor"], yes=True, dry_run=False, list_clients=False
    )
    out = capsys.readouterr().out
    assert "ACP agent command: /opt/vibey/bin/vibey acp" in out
    assert "MCP server command: /opt/vibey/bin/vibey mcp" in out
    assert "zed" in out and "(acp)" in out and "(mcp)" in out
    settings = json.loads((tmp_path / "home" / ".config" / "zed" / "settings.json").read_text())
    assert settings["agent_servers"]["vibey"] == {
        "type": "custom",
        "command": "/opt/vibey/bin/vibey",
        "args": ["acp"],
        "env": {},
    }
    cursor = json.loads((tmp_path / "home" / ".cursor" / "mcp.json").read_text())
    assert cursor["mcpServers"]["vibey"]["args"] == ["mcp"]


def test_a_commented_zed_file_is_refused_with_the_snippet_and_the_others_still_connect(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = _installer(tmp_path)
    zed = tmp_path / "home" / ".config" / "zed" / "settings.json"
    zed.parent.mkdir(parents=True)
    zed.write_text(COMMENTED_ZED)

    with pytest.raises(typer.Exit) as stopped:
        ConnectCommand(installer=installer).run(
            clients=["zed", "cursor"], yes=True, dry_run=False, list_clients=False
        )

    assert stopped.value.exit_code == 1
    assert zed.read_text() == COMMENTED_ZED
    assert not (zed.parent / "settings.json.vibey.bak").exists()
    assert (tmp_path / "home" / ".cursor" / "mcp.json").exists()
    err = capsys.readouterr().err
    assert err.rstrip().endswith(
        '"agent_servers": {"vibey": {"type": "custom", "command": "/opt/vibey/bin/vibey", '
        '"args": ["acp"], "env": {}}}'
    )


def test_a_dry_run_with_a_refused_client_writes_nothing_and_exits_one(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    zed = tmp_path / "home" / ".config" / "zed" / "settings.json"
    zed.parent.mkdir(parents=True)
    zed.write_text(COMMENTED_ZED)
    with pytest.raises(typer.Exit) as stopped:
        ConnectCommand(installer=installer).run(
            clients=["zed", "cursor"], yes=True, dry_run=True, list_clients=False
        )
    assert stopped.value.exit_code == 1
    assert not (tmp_path / "home" / ".cursor").exists()


def test_a_zed_file_already_carrying_the_entry_by_hand_is_left_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = _installer(tmp_path)
    zed = tmp_path / "home" / ".config" / "zed" / "settings.json"
    zed.parent.mkdir(parents=True)
    by_hand = (
        '// mine\n{"agent_servers": {"vibey": {"type": "custom", '
        '"command": "/opt/vibey/bin/vibey", "args": ["acp"], "env": {}},},}\n'
    )
    zed.write_text(by_hand)
    ConnectCommand(installer=installer).run(
        clients=["zed"], yes=True, dry_run=False, list_clients=False
    )
    assert zed.read_text() == by_hand
    assert "All selected clients are already connected." in capsys.readouterr().out


def test_connect_reports_each_surface_of_the_clients_it_planned(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from vibey.cli.llm_tooling import LlmToolingSection
    from vibey.infrastructure.mcp.llm_tooling_probe import LlmToolingProbe

    installer = _installer(tmp_path)
    probe = LlmToolingProbe(
        launcher=lambda: "/opt/vibey/bin/vibey",
        home_dir=lambda: tmp_path / "home",
        project_dir=lambda: tmp_path / "proj",
        platform="darwin",
        shipped_skill=lambda: None,
    )
    ConnectCommand(installer=installer, tooling=LlmToolingSection(probe)).run(
        clients=["zed", "claude_code"], yes=True, dry_run=False, list_clients=False
    )
    out = capsys.readouterr().out.splitlines()
    report = out[out.index("LLM tooling:") + 1 :]
    assert len(report) == 8
    assert report[0].startswith("PASS zed:acp-agent") and "present:" in report[0]
    assert any(
        line.startswith("WARN claude_code:plugin") and "/plugin install vibey@vibey" in line
        for line in report
    )
    assert any(line.startswith("PASS claude_code:mcp-server") for line in report)


def test_the_cli_writes_the_running_installs_own_vibey_never_one_found_on_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import vibey.cli.connect as connect_module

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(connect_module, "running_vibey", lambda: "/pinned/bin/vibey")
    monkeypatch.setattr("shutil.which", lambda *_a, **_k: "/evil/on/path/vibey")
    plan = connect_module.PINNED_INSTALLER.build_plan(["cursor", "zed"])
    assert [item.launch.command for item in plan] == ["/pinned/bin/vibey"] * 2
    assert [item.launch.args for item in plan] == [("mcp",), ("acp",)]
