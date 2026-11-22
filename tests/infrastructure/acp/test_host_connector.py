# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`HostConnector`: `vibey acp`'s `vibey connect` step, user-scope clients only (SP-ACP).

It writes in the user's home, outside the repository, without asking, so it is held narrow:
only clients whose configuration lives under the home folder, only where that client's config
folder already exists (it never creates one), never a project file in the working directory,
each change backed up, idempotent, and one client's broken file never stops the others.
Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from vibey.application.acp.interfaces.host_connector_interface import HostConnectorInterface
from vibey.domain.host_clients import HOST_CLIENT_CATALOG
from vibey.infrastructure.acp.host_connector import HostConnector
from vibey.infrastructure.mcp.host_installer import HostInstaller

VERSION = "9.9.9"


def _connector(tmp_path: Path, *, platform: str = "linux") -> tuple[HostConnector, Path, Path]:
    home, project, state = tmp_path / "home", tmp_path / "project", tmp_path / "state"
    home.mkdir()
    project.mkdir()
    installer = HostInstaller(
        home_dir=lambda: home,
        project_dir=lambda: project,
        platform=platform,
        which=lambda _name: "/usr/local/bin/vibey",
        environ={},
    )
    connector = HostConnector(
        installer=installer,
        catalog=HOST_CLIENT_CATALOG,
        home_dir=lambda: home,
        state_dir=state,
        version=VERSION,
        environ={},
    )
    return connector, home, project


def test_only_user_scope_clients_with_an_existing_config_dir_are_connected(tmp_path: Path) -> None:
    connector, home, project = _connector(tmp_path)
    (home / ".cursor").mkdir()
    (home / ".codex").mkdir()
    # .mcp.json and .vscode/mcp.json are project files: never written into the cwd
    (project / ".vscode").mkdir()

    results = asyncio.run(connector.connect_detected())

    assert json.loads((home / ".cursor" / "mcp.json").read_text())["mcpServers"]["vibey"] == {
        "command": "/usr/local/bin/vibey",
        "args": ["mcp"],
    }
    assert "[mcp_servers.vibey]" in (home / ".codex" / "config.toml").read_text()
    assert not (project / ".mcp.json").exists()
    assert not (project / ".vscode" / "mcp.json").exists()
    # A client whose folder does not exist is not installed here: its folder is never made.
    assert not (home / ".gemini").exists()
    assert not (home / ".config").exists()
    marks = {r.name: r.mark for r in results}
    assert marks["cursor"] == "PASS" and marks["codex"] == "PASS"
    assert marks["gemini_cli"] == "UNKNOWN" and marks["claude_desktop"] == "UNKNOWN"
    assert "claude_code" not in marks and "vscode" not in marks


def test_one_client_error_is_a_warn_and_others_continue(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text("not = [valid")
    (home / ".cursor").mkdir()

    results = asyncio.run(connector.connect_detected())

    marks = {r.name: (r.mark, r.detail) for r in results}
    assert marks["codex"][0] == "WARN" and "invalid TOML" in marks["codex"][1]
    assert marks["cursor"][0] == "PASS"
    assert (home / ".codex" / "config.toml").read_text() == "not = [valid"  # left as it was
    assert (home / ".cursor" / "mcp.json").exists()


def test_a_file_that_cannot_be_written_is_a_warn_for_that_client_only(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    (home / ".gemini").mkdir()
    (home / ".cursor" / "mcp.json").mkdir()  # a directory where the file should be

    results = asyncio.run(connector.connect_detected())

    marks = {r.name: r.mark for r in results}
    assert marks["cursor"] == "WARN" and marks["gemini_cli"] == "PASS"


def test_an_existing_config_is_backed_up_and_a_second_run_changes_nothing(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    original = json.dumps({"mcpServers": {"other": {"command": "x"}}})
    (home / ".cursor" / "mcp.json").write_text(original)

    asyncio.run(connector.connect_detected())
    after = (home / ".cursor" / "mcp.json").read_text()
    again = asyncio.run(connector.connect_detected())

    assert (home / ".cursor" / "mcp.json.vibey.bak").read_text() == original
    assert json.loads(after)["mcpServers"]["other"] == {"command": "x"}
    assert (home / ".cursor" / "mcp.json").read_text() == after
    cursor = next(r for r in again if r.name == "cursor")
    assert cursor.mark == "PASS" and "already" in cursor.detail


def test_the_marker_lists_what_was_connected_and_says_so_afterwards(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    assert connector.already_connected() is False

    asyncio.run(connector.connect_detected())

    marker = tmp_path / "state" / f"acp-connect-{VERSION}.json"
    assert json.loads(marker.read_text()) == {"version": VERSION, "clients": ["cursor"]}
    assert marker.stat().st_mode & 0o777 == 0o600
    assert connector.already_connected() is True


@pytest.mark.parametrize(
    "content",
    [b"{not json", b"[]", b'{"version": "1.0.0", "clients": []}', b"\xff\xfe", b'{"version": 1}'],
    ids=["corrupt", "not-an-object", "another-version", "not-utf8", "version-not-text"],
)
def test_a_marker_that_cannot_be_read_means_not_connected(tmp_path: Path, content: bytes) -> None:
    connector, _, _ = _connector(tmp_path)
    marker = tmp_path / "state" / f"acp-connect-{VERSION}.json"
    marker.parent.mkdir()
    marker.write_bytes(content)

    assert connector.already_connected() is False


def test_a_marker_that_cannot_be_written_is_a_warn_not_a_crash(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    (tmp_path / "state").write_text("a file where the state folder should be")

    results = asyncio.run(connector.connect_detected())

    assert results[-1].mark == "WARN" and results[-1].name == "connect-marker"
    assert (home / ".cursor" / "mcp.json").exists()
    assert connector.already_connected() is False


def test_a_target_outside_the_home_folder_is_never_written(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    # The installer resolves paths against another home than the connector checks against.
    connector = HostConnector(
        installer=HostInstaller(
            home_dir=lambda: elsewhere, project_dir=lambda: tmp_path, platform="linux"
        ),
        catalog=HOST_CLIENT_CATALOG,
        home_dir=lambda: home,
        state_dir=tmp_path / "state",
        version=VERSION,
    )
    (elsewhere / ".cursor").mkdir(parents=True)

    results = asyncio.run(connector.connect_detected())

    assert not (elsewhere / ".cursor" / "mcp.json").exists()
    assert {r.mark for r in results} == {"UNKNOWN"}


def test_the_connector_satisfies_its_interface(tmp_path: Path) -> None:
    connector, _, _ = _connector(tmp_path)
    assert isinstance(connector, HostConnectorInterface)


def test_a_warned_client_leaves_no_marker_so_the_next_run_tries_again(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text("not = [valid")
    (home / ".cursor").mkdir()

    asyncio.run(connector.connect_detected())

    assert not (tmp_path / "state" / f"acp-connect-{VERSION}.json").exists()
    assert connector.already_connected() is False
    (home / ".codex" / "config.toml").write_text("")
    asyncio.run(connector.connect_detected())
    assert connector.already_connected() is True


def test_a_client_installed_after_the_marker_is_connected_next_time(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    asyncio.run(connector.connect_detected())
    assert connector.already_connected() is True

    (home / ".gemini").mkdir()  # Gemini CLI installed since

    assert connector.already_connected() is False


def test_a_marker_whose_clients_are_not_a_list_means_not_connected(tmp_path: Path) -> None:
    connector, _, _ = _connector(tmp_path)
    marker = tmp_path / "state" / f"acp-connect-{VERSION}.json"
    marker.parent.mkdir()
    marker.write_text(json.dumps({"version": VERSION, "clients": "cursor"}))

    assert connector.already_connected() is False


def test_a_config_folder_symlinked_out_of_home_is_not_written(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (home / ".cursor").symlink_to(outside, target_is_directory=True)

    results = asyncio.run(connector.connect_detected())

    cursor = next(r for r in results if r.name == "cursor")
    assert cursor.mark == "UNKNOWN" and "not inside your home folder" in cursor.detail
    assert list(outside.iterdir()) == []


def test_zed_is_connected_as_an_acp_agent_server_when_it_is_installed(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".config" / "zed").mkdir(parents=True)

    results = asyncio.run(connector.connect_detected())

    settings = json.loads((home / ".config" / "zed" / "settings.json").read_text())
    assert settings["agent_servers"]["vibey"] == {
        "type": "custom",
        "command": "/usr/local/bin/vibey",
        "args": ["acp"],
        "env": {},
    }
    assert {r.name: r.mark for r in results}["zed"] == "PASS"


def test_commented_zed_settings_are_a_warn_with_the_snippet_and_never_rewritten(
    tmp_path: Path,
) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    settings = home / ".config" / "zed" / "settings.json"
    settings.parent.mkdir(parents=True)
    commented = '// Zed settings\n{\n  "theme": "One Dark",\n}\n'
    settings.write_text(commented)

    results = {r.name: r for r in asyncio.run(connector.connect_detected())}

    assert settings.read_text() == commented
    assert not (settings.parent / "settings.json.vibey.bak").exists()
    assert results["zed"].mark == "WARN"
    assert results["zed"].detail.endswith(
        '"agent_servers": {"vibey": {"type": "custom", "command": "/usr/local/bin/vibey", '
        '"args": ["acp"], "env": {}}}'
    )
    assert results["cursor"].mark == "PASS"
    assert not connector.already_connected()


def test_a_deeply_nested_config_is_that_clients_warn_never_a_crash(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    (home / ".codex").mkdir()
    (home / ".cursor" / "mcp.json").write_text("// c\n" + "[" * 200_000)
    (home / ".codex" / "config.toml").write_text("x = " + "[" * 200_000)
    (home / ".gemini").mkdir()

    results = {r.name: r for r in asyncio.run(connector.connect_detected())}

    assert results["cursor"].mark == "WARN" and "invalid JSON" in results["cursor"].detail
    assert results["codex"].mark == "WARN" and "invalid TOML" in results["codex"].detail
    assert results["gemini_cli"].mark == "PASS"


def test_the_unattended_step_keeps_a_customised_zed_entry(tmp_path: Path) -> None:
    connector, home, _ = _connector(tmp_path)
    settings = home / ".config" / "zed" / "settings.json"
    settings.parent.mkdir(parents=True)
    mine = {
        "type": "custom",
        "command": "/old/vibey",
        "args": ["acp", "--no-bootstrap"],
        "env": {"VIBEY_CONFIG": "/x"},
    }
    settings.write_text(json.dumps({"agent_servers": {"vibey": mine}}))

    asyncio.run(connector.connect_detected())

    written = json.loads(settings.read_text())["agent_servers"]["vibey"]
    assert written == {**mine, "command": "/usr/local/bin/vibey"}


def test_a_config_folder_that_cannot_be_looked_into_is_not_installed(tmp_path: Path) -> None:
    import os

    if os.geteuid() == 0:
        pytest.skip("root can look into anything")
    connector, home, _ = _connector(tmp_path)
    (home / ".config" / "zed").mkdir(parents=True)
    (home / ".config").chmod(0)
    try:
        results = {r.name: r.mark for r in asyncio.run(connector.connect_detected())}
        connected = connector.already_connected()
    finally:
        (home / ".config").chmod(0o700)
    assert results["zed"] == "UNKNOWN"
    assert connected is True


def test_an_installer_aiming_at_a_folder_that_is_not_there_writes_nothing(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    _, home, _ = _connector(tmp_path)
    (home / ".cursor").mkdir()
    connector = HostConnector(
        installer=HostInstaller(
            home_dir=lambda: elsewhere, project_dir=lambda: tmp_path, platform="linux"
        ),
        home_dir=lambda: home,
        state_dir=tmp_path / "state",
        version=VERSION,
        environ={},
    )

    results = {r.name: r for r in asyncio.run(connector.connect_detected())}

    assert results["cursor"].mark == "UNKNOWN" and "does not exist" in results["cursor"].detail
    assert not elsewhere.exists()
