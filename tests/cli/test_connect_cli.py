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


# ----------------------------------------------- fix round 1: hostile and customised files


def test_a_deeply_nested_project_config_is_refused_and_the_others_still_connect(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = _installer(tmp_path)
    (tmp_path / "proj" / ".mcp.json").write_text("[" * 200_000)
    with pytest.raises(typer.Exit) as stopped:
        ConnectCommand(installer=installer).run(
            clients=["claude_code", "cursor"], yes=True, dry_run=False, list_clients=False
        )
    assert stopped.value.exit_code == 1
    assert (tmp_path / "home" / ".cursor" / "mcp.json").exists()
    err = capsys.readouterr().err
    assert "claude_code was not connected" in err and "nested too deeply" in err
    assert (tmp_path / "proj" / ".mcp.json").read_text() == "[" * 200_000


@pytest.mark.parametrize(
    ("content", "says"),
    [
        (b"\xff\xfe{", "UnicodeDecodeError"),
        ("x = " + "[" * 200_000, "invalid TOML"),
    ],
)
def test_an_unreadable_or_unparseable_config_is_one_line_for_that_client(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], content: bytes | str, says: str
) -> None:
    installer = _installer(tmp_path)
    codex = tmp_path / "home" / ".codex" / "config.toml"
    codex.parent.mkdir(parents=True)
    if isinstance(content, bytes):
        codex.write_bytes(content)
    else:
        codex.write_text(content)
    with pytest.raises(typer.Exit):
        ConnectCommand(installer=installer).run(
            clients=["codex", "cursor"], yes=True, dry_run=False, list_clients=False
        )
    err = [line for line in capsys.readouterr().err.splitlines() if line]
    assert len(err) == 1 and err[0].startswith("Error: codex was not connected: ")
    assert says in err[0]


def test_a_config_vibey_may_not_read_is_refused_for_that_client_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import os

    if os.geteuid() == 0:
        pytest.skip("root reads anything")
    installer = _installer(tmp_path)
    cursor = tmp_path / "home" / ".cursor" / "mcp.json"
    cursor.parent.mkdir(parents=True)
    cursor.write_text("{}")
    cursor.chmod(0)
    try:
        with pytest.raises(typer.Exit):
            ConnectCommand(installer=installer).run(
                clients=["cursor", "zed"], yes=True, dry_run=False, list_clients=False
            )
    finally:
        cursor.chmod(0o600)
    assert "PermissionError" in capsys.readouterr().err
    assert (tmp_path / "home" / ".config" / "zed" / "settings.json").exists()


def test_a_write_that_fails_is_one_error_line_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class _Failing:
        def build_plan(self, requested=None):
            return _installer(tmp_path).build_plan(requested)

        def apply_plan(self, plan):
            raise OSError(28, "No space left on device")

    with pytest.raises(typer.Exit) as stopped:
        ConnectCommand(installer=_Failing()).run(
            clients=["cursor"], yes=True, dry_run=False, list_clients=False
        )
    assert stopped.value.exit_code == 1
    assert "a file could not be written: OSError: [Errno 28] No space left" in (
        capsys.readouterr().err
    )


def test_a_customised_zed_entry_is_kept_through_a_connect(tmp_path: Path) -> None:
    installer = _installer(tmp_path)
    zed = tmp_path / "home" / ".config" / "zed" / "settings.json"
    zed.parent.mkdir(parents=True)
    mine = {
        "type": "custom",
        "command": "/old/vibey",
        "args": ["acp", "--no-bootstrap"],
        "env": {"VIBEY_CONFIG": "/x"},
    }
    zed.write_text(
        json.dumps(
            {"buffer_font_family": "Fira Código", "agent_servers": {"vibey": mine}},
            indent=4,
            ensure_ascii=False,
        )
    )
    ConnectCommand(installer=installer).run(
        clients=["zed"], yes=True, dry_run=False, list_clients=False
    )
    text = zed.read_text()
    assert "Fira Código" in text and '\n    "agent_servers"' in text
    assert json.loads(text)["agent_servers"]["vibey"] == {**mine, "command": "/opt/vibey/bin/vibey"}
    before = zed.read_text()
    ConnectCommand(installer=installer).run(
        clients=["zed"], yes=True, dry_run=False, list_clients=False
    )
    assert zed.read_text() == before


def test_the_refusal_is_shown_even_when_the_question_is_declined(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    installer = _installer(tmp_path)
    zed = tmp_path / "home" / ".config" / "zed" / "settings.json"
    zed.parent.mkdir(parents=True)
    zed.write_text(COMMENTED_ZED)
    with pytest.raises(typer.Exit):
        ConnectCommand(installer=installer, confirm=lambda _: False).run(
            clients=["zed", "cursor"], yes=False, dry_run=False, list_clients=False
        )
    assert '"args": ["acp"]' in capsys.readouterr().err


def test_zed_on_linux_is_written_where_xdg_config_home_points(tmp_path: Path) -> None:
    home = tmp_path / "home"
    xdg = home / ".xdg"
    installer = HostInstaller(
        home_dir=lambda: home,
        project_dir=lambda: tmp_path,
        platform="linux",
        which=lambda _: "/opt/vibey/bin/vibey",
        environ={"XDG_CONFIG_HOME": str(xdg)},
    )
    home.mkdir()
    ConnectCommand(installer=installer).run(
        clients=["zed"], yes=True, dry_run=False, list_clients=False
    )
    assert (xdg / "zed" / "settings.json").exists()
    assert not (home / ".config").exists()


def test_the_guides_no_bootstrap_entry_counts_as_connected() -> None:
    import re

    from vibey.domain.host_clients import HOST_CLIENT_CATALOG, McpLaunchCommand

    guide = (Path(__file__).parents[2] / "docs" / "guides" / "acp.md").read_text()
    args = json.loads(re.search(r'"args": (\["acp", "--no-bootstrap"\])', guide).group(1))
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None
    entry = {"type": "custom", "command": "/v/vibey", "args": args, "env": {}}
    assert HOST_CLIENT_CATALOG.carries(
        zed, McpLaunchCommand("/v/vibey", ("acp",)), json.dumps({"agent_servers": {"vibey": entry}})
    )
