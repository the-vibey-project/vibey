# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the pure `vibey connect` planner and config merger (ADR-0100)."""

from __future__ import annotations

import json
import tomllib

import pytest

from vibey.domain.host_clients import (
    HOST_CLIENT_CATALOG,
    HOST_CLIENTS,
    PYTHON_FALLBACK_CODE,
    HostClientError,
    HostClients,
    McpLaunchCommand,
)
from vibey.domain.interfaces.host_clients_interface import HostClientsInterface


def test_catalog_satisfies_interface_and_lists_all_clients() -> None:
    assert isinstance(HOST_CLIENT_CATALOG, HostClientsInterface)
    assert HOST_CLIENT_CATALOG.all() == HOST_CLIENTS
    assert [c.client_id for c in HOST_CLIENTS] == [
        "claude_code",
        "claude_desktop",
        "codex",
        "cursor",
        "vscode",
        "gemini_cli",
    ]


def test_by_id_and_resolve_clients_handle_normalization_dedup_and_unknowns() -> None:
    assert HOST_CLIENT_CATALOG.by_id("  Claude-Code ") is not None
    assert HOST_CLIENT_CATALOG.by_id("unknown") is None

    assert HOST_CLIENT_CATALOG.resolve_clients(None) == HOST_CLIENTS
    assert HOST_CLIENT_CATALOG.resolve_clients([]) == HOST_CLIENTS

    subset = HOST_CLIENT_CATALOG.resolve_clients(["codex", "claude-code", "codex"])
    assert [c.client_id for c in subset] == ["codex", "claude_code"]

    with pytest.raises(HostClientError, match="unknown client 'bogus'"):
        HOST_CLIENT_CATALOG.resolve_clients(["bogus"])


def test_resolve_launch_prefers_absolute_vibey_and_falls_back_to_python() -> None:
    direct = HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey="/opt/homebrew/bin/vibey",
        python_executable="/usr/bin/python3",
    )
    assert direct == McpLaunchCommand(command="/opt/homebrew/bin/vibey", args=("mcp",))
    assert direct.display() == "/opt/homebrew/bin/vibey mcp"

    fallback = HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey="   ",
        python_executable="/venv/bin/python3",
    )
    assert fallback == McpLaunchCommand(
        command="/venv/bin/python3",
        args=("-c", PYTHON_FALLBACK_CODE),
    )


def test_config_paths_across_platforms() -> None:
    by_id = {c.client_id: c for c in HOST_CLIENTS}
    assert (
        by_id["claude_code"].config_path(
            home_dir="/Users/alice/", project_dir="/repo/", platform="darwin"
        )
        == "/repo/.mcp.json"
    )
    assert (
        by_id["claude_desktop"].config_path(
            home_dir="/Users/alice", project_dir="/repo", platform="darwin"
        )
        == "/Users/alice/Library/Application Support/Claude/claude_desktop_config.json"
    )
    assert (
        by_id["claude_desktop"].config_path(
            home_dir="/home/alice", project_dir="/repo", platform="linux"
        )
        == "/home/alice/.config/Claude/claude_desktop_config.json"
    )
    assert (
        by_id["codex"].config_path(home_dir="/Users/alice", project_dir="/repo", platform="darwin")
        == "/Users/alice/.codex/config.toml"
    )
    assert (
        by_id["cursor"].config_path(home_dir="/Users/alice", project_dir="/repo", platform="darwin")
        == "/Users/alice/.cursor/mcp.json"
    )
    assert (
        by_id["vscode"].config_path(home_dir="/Users/alice", project_dir="/repo", platform="darwin")
        == "/repo/.vscode/mcp.json"
    )
    assert (
        by_id["gemini_cli"].config_path(
            home_dir="/Users/alice", project_dir="/repo", platform="darwin"
        )
        == "/Users/alice/.gemini/settings.json"
    )


def test_plan_one_json_create_merge_and_idempotency() -> None:
    launch = McpLaunchCommand(command="/usr/local/bin/vibey", args=("mcp",))
    vscode = HOST_CLIENT_CATALOG.by_id("vscode")
    assert vscode is not None

    # 1. Create from None
    created = HOST_CLIENT_CATALOG.plan_one(
        vscode,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=None,
    )
    assert created.action == "create"
    assert created.backup_path is None
    doc = json.loads(created.new_content)
    assert doc == {
        "servers": {
            "vibey": {
                "type": "stdio",
                "command": "/usr/local/bin/vibey",
                "args": ["mcp"],
            }
        }
    }

    # 2. Re-running on exact content -> unchanged
    unchanged = HOST_CLIENT_CATALOG.plan_one(
        vscode,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=created.new_content,
    )
    assert unchanged.action == "unchanged"
    assert unchanged.backup_path is None

    # 3. Merge into existing file with sibling server and blank existing content
    claude_code = HOST_CLIENT_CATALOG.by_id("claude_code")
    assert claude_code is not None
    updated = HOST_CLIENT_CATALOG.plan_one(
        claude_code,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content='{"otherKey": 1, "mcpServers": {"github": {"command": "gh"}}}',
    )
    assert updated.action == "update"
    assert updated.backup_path == "/repo/.mcp.json.vibey.bak"
    merged_doc = json.loads(updated.new_content)
    assert merged_doc["otherKey"] == 1
    assert merged_doc["mcpServers"]["github"] == {"command": "gh"}
    assert merged_doc["mcpServers"]["vibey"] == {
        "command": "/usr/local/bin/vibey",
        "args": ["mcp"],
    }


def test_plan_one_toml_create_merge_replace_and_idempotency() -> None:
    launch = McpLaunchCommand(command="/usr/local/bin/vibey", args=("mcp",))
    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert codex is not None

    # 1. Create from None
    created = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=None,
    )
    assert created.action == "create"
    assert tomllib.loads(created.new_content) == {
        "mcp_servers": {"vibey": {"command": "/usr/local/bin/vibey", "args": ["mcp"]}}
    }

    # 2. Unchanged when already matching
    unchanged = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=created.new_content,
    )
    assert unchanged.action == "unchanged"

    # 3. Append to existing TOML with other settings
    appended = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content='model = "o3"\n\n[mcp_servers.other]\ncommand = "other"\n',
    )
    assert appended.action == "update"
    parsed_appended = tomllib.loads(appended.new_content)
    assert parsed_appended["model"] == "o3"
    assert parsed_appended["mcp_servers"]["other"]["command"] == "other"
    assert parsed_appended["mcp_servers"]["vibey"]["command"] == "/usr/local/bin/vibey"

    # 4. Replace outdated [mcp_servers.vibey] section followed by another section
    outdated = (
        "[mcp_servers.vibey]\n"
        'command = "/old/vibey"\n'
        'args = ["mcp"]\n\n'
        "[mcp_servers.other]\n"
        'command = "other"\n'
    )
    replaced = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=outdated,
    )
    assert replaced.action == "update"
    parsed_replaced = tomllib.loads(replaced.new_content)
    assert parsed_replaced["mcp_servers"]["vibey"]["command"] == "/usr/local/bin/vibey"
    assert parsed_replaced["mcp_servers"]["other"]["command"] == "other"

    # 5. Replace outdated [mcp_servers.vibey] at EOF without trailing newline
    outdated_eof = '[mcp_servers.vibey]\ncommand = "/old/vibey"\nargs = ["mcp"]'
    replaced_eof = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content=outdated_eof,
    )
    assert replaced_eof.new_content.endswith("\n")

    # 6. Append to existing TOML that has no mcp_servers table at all
    no_mcp_table = HOST_CLIENT_CATALOG.plan_one(
        codex,
        home_dir="/Users/alice",
        project_dir="/repo",
        platform="darwin",
        launch=launch,
        existing_content='model = "o3"\n',
    )
    assert no_mcp_table.action == "update"
    assert (
        tomllib.loads(no_mcp_table.new_content)["mcp_servers"]["vibey"]["command"]
        == "/usr/local/bin/vibey"
    )


@pytest.mark.parametrize(
    ("client_id", "content", "match"),
    [
        ("claude_code", "{bad json", "invalid JSON"),
        ("claude_code", "[1, 2, 3]", "expected a top-level JSON object"),
        ("claude_code", '{"mcpServers": "not-an-object"}', "'mcpServers' must be a JSON object"),
        ("codex", "invalid = [toml", "invalid TOML"),
        ("codex", 'mcp_servers = "not-a-table"\n', "'mcp_servers' must be a TOML table"),
    ],
)
def test_plan_one_rejects_corrupt_existing_files(client_id: str, content: str, match: str) -> None:
    spec = HostClients().by_id(client_id)
    assert spec is not None
    launch = McpLaunchCommand(command="vibey", args=("mcp",))
    with pytest.raises(HostClientError, match=match):
        HostClients().plan_one(
            spec,
            home_dir="/Users/alice",
            project_dir="/repo",
            platform="darwin",
            launch=launch,
            existing_content=content,
        )
