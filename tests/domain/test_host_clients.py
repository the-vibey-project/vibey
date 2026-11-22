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
        "zed",
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


# ------------------------------------------------------------------ Zed, an ACP agent server


ZED_LAUNCH = McpLaunchCommand(command="/usr/local/bin/vibey", args=("acp",))
ZED_ENTRY = {"type": "custom", "command": "/usr/local/bin/vibey", "args": ["acp"], "env": {}}


def _zed_plan(existing: str | None, launch: McpLaunchCommand = ZED_LAUNCH):
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None
    return HOST_CLIENT_CATALOG.plan_one(
        zed,
        home_dir="/home/alice",
        project_dir="/repo",
        platform="linux",
        launch=launch,
        existing_content=existing,
    )


def test_zed_is_a_user_scope_acp_client_whose_settings_live_in_dot_config_on_both_platforms() -> (
    None
):
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None
    assert (zed.protocol, zed.entry_type, zed.scope, zed.root_key) == (
        "acp",
        "custom",
        "user",
        "agent_servers",
    )
    for platform, home in (("darwin", "/Users/alice"), ("linux", "/home/alice")):
        assert (
            zed.config_path(home_dir=home, project_dir="/repo", platform=platform)
            == f"{home}/.config/zed/settings.json"
        )
    assert all(spec.protocol == "mcp" for spec in HOST_CLIENTS if spec.client_id != "zed")


def test_zed_entry_is_a_custom_agent_server_running_vibey_acp() -> None:
    item = _zed_plan(None)
    assert item.action == "create"
    doc = json.loads(item.new_content)
    assert doc["agent_servers"]["vibey"] == ZED_ENTRY


def test_zed_keeps_other_settings_and_other_agent_servers() -> None:
    existing = json.dumps(
        {
            "theme": "One Dark",
            "agent_servers": {"Other": {"type": "custom", "command": "node", "args": []}},
        }
    )
    item = _zed_plan(existing)
    assert item.action == "update"
    assert item.backup_path == "/home/alice/.config/zed/settings.json.vibey.bak"
    doc = json.loads(item.new_content)
    assert doc["theme"] == "One Dark"
    assert doc["agent_servers"]["Other"] == {"type": "custom", "command": "node", "args": []}
    assert doc["agent_servers"]["vibey"] == ZED_ENTRY
    assert _zed_plan(item.new_content).action == "unchanged"


COMMENTED_ZED = """// Zed settings
//
// For information on how to configure Zed, see https://zed.dev/docs/configuring-zed
{
  "theme": "One Dark", // the theme
  /* a block comment */
  "buffer_font_size": 15,
}
"""


def test_commented_zed_settings_are_refused_with_the_snippet_and_not_rewritten() -> None:
    with pytest.raises(HostClientError, match=r'"args": \["acp"\]') as refused:
        _zed_plan(COMMENTED_ZED)
    message = str(refused.value)
    snippet = (
        '"agent_servers": {"vibey": {"type": "custom", "command": "/usr/local/bin/vibey", '
        '"args": ["acp"], "env": {}}}'
    )
    assert message.endswith(snippet)
    assert "/home/alice/.config/zed/settings.json" in message


def test_a_commented_zed_file_that_already_carries_the_entry_is_left_unchanged() -> None:
    by_hand = COMMENTED_ZED.replace(
        '"buffer_font_size": 15,',
        '"buffer_font_size": 15,\n  "agent_servers": { // pasted\n'
        '    "vibey": {"type": "custom", "command": "/usr/local/bin/vibey",'
        ' "args": ["acp"], "env": {},},\n  },',
    )
    item = _zed_plan(by_hand)
    assert item.action == "unchanged"
    assert item.new_content == by_hand


def test_a_commented_file_whose_entry_differs_is_still_refused_never_rewritten() -> None:
    by_hand = COMMENTED_ZED.replace(
        '"buffer_font_size": 15,',
        '"agent_servers": {"vibey": {"type": "custom", "command": "vibey", "args": ["acp"]}},',
    )
    with pytest.raises(HostClientError, match="not strict JSON"):
        _zed_plan(by_hand)


def test_comment_markers_inside_strings_are_text_not_comments() -> None:
    lenient = '{"url": "https://zed.dev/docs", "q": "a \\" // b", "agent_servers": {"vibey": '
    lenient += json.dumps(ZED_ENTRY) + ",},}"
    assert _zed_plan(lenient).action == "unchanged"


@pytest.mark.parametrize(
    "content",
    [
        "// only a comment\n",
        '{"a": 1 /* never closed',
        '{"a": "never closed',
        "// x\n[1, 2]",
        '// x\n{"agent_servers": [],}',
    ],
)
def test_a_file_that_is_not_strict_json_and_holds_no_entry_is_refused(content: str) -> None:
    with pytest.raises(HostClientError, match=r'"agent_servers": \{"vibey"'):
        _zed_plan(content)


def test_an_mcp_client_with_invalid_json_ends_with_its_own_snippet() -> None:
    cursor = HOST_CLIENT_CATALOG.by_id("cursor")
    assert cursor is not None
    launch = McpLaunchCommand(command="/usr/local/bin/vibey", args=("mcp",))
    with pytest.raises(HostClientError, match="invalid JSON") as refused:
        HOST_CLIENT_CATALOG.plan_one(
            cursor,
            home_dir="/home/alice",
            project_dir="/repo",
            platform="linux",
            launch=launch,
            existing_content="{bad json",
        )
    assert str(refused.value).endswith(
        '"mcpServers": {"vibey": {"command": "/usr/local/bin/vibey", "args": ["mcp"]}}'
    )


def test_mcp_clients_still_launch_vibey_mcp() -> None:
    assert HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey="/usr/local/bin/vibey", python_executable="/usr/bin/python3"
    ) == McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))
    assert HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey="/usr/local/bin/vibey", python_executable="/usr/bin/python3", protocol="mcp"
    ) == McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))


def test_acp_clients_launch_vibey_acp_or_the_python_fallback_running_acp() -> None:
    assert HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey="/usr/local/bin/vibey", python_executable="/usr/bin/python3", protocol="acp"
    ) == McpLaunchCommand("/usr/local/bin/vibey", ("acp",))
    fallback = HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey=None, python_executable="/venv/bin/python3", protocol="acp"
    )
    assert fallback == McpLaunchCommand(
        "/venv/bin/python3",
        ("-c", "import sys; from vibey.cli.main import run; run(['acp', *sys.argv[1:]])"),
    )


def test_the_snippet_is_the_entry_connect_would_write() -> None:
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    vscode = HOST_CLIENT_CATALOG.by_id("vscode")
    assert zed is not None and vscode is not None
    assert HOST_CLIENT_CATALOG.snippet(zed, ZED_LAUNCH) == (
        '"agent_servers": {"vibey": {"type": "custom", "command": "/usr/local/bin/vibey", '
        '"args": ["acp"], "env": {}}}'
    )
    assert HOST_CLIENT_CATALOG.snippet(vscode, McpLaunchCommand("/a b/vibey", ("mcp",))) == (
        '"servers": {"vibey": {"type": "stdio", "command": "/a b/vibey", "args": ["mcp"]}}'
    )


def test_each_client_names_the_folder_that_says_it_is_installed() -> None:
    by_id = {c.client_id: c for c in HOST_CLIENTS}

    def where(client_id: str, platform: str) -> str:
        return by_id[client_id].presence_path(home_dir="/h/", platform=platform)

    assert where("claude_code", "darwin") == "/h/.claude"
    assert where("vscode", "darwin") == "/h/Library/Application Support/Code"
    assert where("vscode", "linux") == "/h/.config/Code"
    assert where("zed", "darwin") == "/h/.config/zed"
    assert where("cursor", "linux") == "/h/.cursor"
    assert where("claude_desktop", "darwin") == "/h/Library/Application Support/Claude"


def test_carries_reads_the_entry_however_the_file_is_laid_out() -> None:
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert zed is not None and codex is not None
    compact = json.dumps({"agent_servers": {"vibey": ZED_ENTRY}})
    assert HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, compact)
    assert HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, "// c\n" + compact[:-1] + ",}")
    assert not HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, None)
    assert not HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, "  ")
    assert not HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, '{"agent_servers": []}')
    assert not HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, "[1]")
    mcp = McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))
    toml = '[mcp_servers.vibey]\ncommand = "/usr/local/bin/vibey"\nargs = ["mcp"]\n'
    assert HOST_CLIENT_CATALOG.carries(codex, mcp, toml)
    assert not HOST_CLIENT_CATALOG.carries(codex, McpLaunchCommand("vibey", ("mcp",)), toml)
    assert not HOST_CLIENT_CATALOG.carries(codex, mcp, "[broken")
    assert not HOST_CLIENT_CATALOG.carries(codex, mcp, 'mcp_servers = "x"\n')


# ------------------------------------------------------- fix round 1: hostile and customised files

DEEP_JSON = ["[" * 200_000, "// c\n" + "[" * 200_000, '{"agent_servers": ' + "[" * 200_000]


@pytest.mark.parametrize("content", DEEP_JSON)
def test_json_nested_too_deeply_is_refused_with_the_snippet_never_a_traceback(content: str) -> None:
    with pytest.raises(HostClientError, match=r'"agent_servers": \{"vibey"'):
        _zed_plan(content)
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None
    assert not HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, content)


def test_toml_nested_too_deeply_is_refused_never_a_traceback() -> None:
    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert codex is not None
    deep = "x = " + "[" * 200_000
    mcp = McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))
    with pytest.raises(HostClientError, match="invalid TOML"):
        HOST_CLIENT_CATALOG.plan_one(
            codex,
            home_dir="/h",
            project_dir="/p",
            platform="linux",
            launch=mcp,
            existing_content=deep,
        )
    assert not HOST_CLIENT_CATALOG.carries(codex, mcp, deep)


def test_a_customised_zed_entry_keeps_its_env_extra_args_and_keys_through_a_connect() -> None:
    mine = {
        "type": "custom",
        "command": "/old/bin/vibey",
        "args": ["acp", "--no-bootstrap"],
        "env": {"VIBEY_CONFIG": "/x"},
        "default_mode": "observe",
    }
    item = _zed_plan(json.dumps({"agent_servers": {"vibey": mine}}))
    assert item.action == "update"
    assert json.loads(item.new_content)["agent_servers"]["vibey"] == {
        **mine,
        "command": "/usr/local/bin/vibey",
    }


def test_an_entry_running_the_pinned_launcher_with_extra_flags_and_env_is_connected() -> None:
    mine = {**ZED_ENTRY, "args": ["acp", "--no-bootstrap"], "env": {"A": "b"}}
    existing = json.dumps({"agent_servers": {"vibey": mine}})
    item = _zed_plan(existing)
    assert item.action == "unchanged" and item.new_content == existing
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None
    assert HOST_CLIENT_CATALOG.carries(zed, ZED_LAUNCH, existing)


@pytest.mark.parametrize(
    "entry",
    [
        {**ZED_ENTRY, "args": ["mcp"]},
        {**ZED_ENTRY, "type": "stdio"},
        {**ZED_ENTRY, "env": "not a table"},
        {**ZED_ENTRY, "args": "acp"},
        "not an object",
    ],
)
def test_an_entry_that_does_not_run_vibey_acp_is_rewritten(entry: object) -> None:
    item = _zed_plan(json.dumps({"agent_servers": {"vibey": entry}}))
    assert item.action == "update"
    written = json.loads(item.new_content)["agent_servers"]["vibey"]
    assert written["command"] == "/usr/local/bin/vibey" and written["args"][0] == "acp"
    assert written["type"] == "custom" and isinstance(written["env"], dict)


def test_a_python_fallback_entry_keeps_its_flags_when_the_launcher_changes() -> None:
    fallback = {
        **ZED_ENTRY,
        "command": "/usr/bin/python3",
        "args": ["-c", "from vibey.cli.main import run; run(['acp'])", "--no-bootstrap"],
    }
    item = _zed_plan(json.dumps({"agent_servers": {"vibey": fallback}}))
    assert json.loads(item.new_content)["agent_servers"]["vibey"]["args"] == [
        "acp",
        "--no-bootstrap",
    ]


def test_a_file_already_carrying_the_entry_is_never_reformatted() -> None:
    laid_out = json.dumps(
        {"buffer_font_family": "Fira Código", "agent_servers": {"vibey": ZED_ENTRY}},
        indent=4,
        ensure_ascii=True,
    )
    item = _zed_plan(laid_out)
    assert item.action == "unchanged" and item.new_content == laid_out


def test_a_rewrite_keeps_non_ascii_text_and_the_files_indentation() -> None:
    four = json.dumps({"buffer_font_family": "Fira Código"}, indent=4, ensure_ascii=False)
    item = _zed_plan(four)
    assert "Fira Código" in item.new_content
    assert '\n    "buffer_font_family"' in item.new_content
    tabbed = '{\n\t"theme": "x"\n}'
    assert '\n\t"theme"' in _zed_plan(tabbed).new_content
    assert '\n  "agent_servers"' in _zed_plan("{}").new_content


def test_a_byte_order_mark_is_read_past_and_kept() -> None:
    bom = "﻿" + json.dumps({"theme": "x"})
    item = _zed_plan(bom)
    assert item.new_content.startswith("﻿{")
    assert json.loads(item.new_content[1:])["agent_servers"]["vibey"] == ZED_ENTRY
    carried = "﻿" + json.dumps({"agent_servers": {"vibey": ZED_ENTRY}})
    assert _zed_plan(carried).action == "unchanged"


def test_a_codex_entry_keeps_its_extra_flags_and_counts_as_connected_with_them() -> None:
    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert codex is not None
    mcp = McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))

    def plan(content: str):
        return HOST_CLIENT_CATALOG.plan_one(
            codex,
            home_dir="/h",
            project_dir="/p",
            platform="linux",
            launch=mcp,
            existing_content=content,
        )

    connected = '[mcp_servers.vibey]\ncommand = "/usr/local/bin/vibey"\nargs = ["mcp", "--x"]\n'
    assert plan(connected).action == "unchanged"
    old = '[mcp_servers.vibey]\ncommand = "/old/vibey"\nargs = ["mcp", "--x"]\n'
    assert tomllib.loads(plan(old).new_content)["mcp_servers"]["vibey"]["args"] == ["mcp", "--x"]
    assert not HOST_CLIENT_CATALOG.carries(codex, mcp, '[mcp_servers.vibey]\ncommand = "x"\n')


def test_zed_on_linux_follows_an_absolute_xdg_config_home_and_macos_never_does() -> None:
    zed = HOST_CLIENT_CATALOG.by_id("zed")
    assert zed is not None

    def where(platform: str, xdg: str | None) -> str:
        return zed.config_path(
            home_dir="/home/a", project_dir="/p", platform=platform, xdg_config_home=xdg
        )

    assert where("linux", "/home/a/.xdg/") == "/home/a/.xdg/zed/settings.json"
    assert where("linux", "relative/xdg") == "/home/a/.config/zed/settings.json"
    assert where("linux", None) == "/home/a/.config/zed/settings.json"
    assert where("darwin", "/home/a/.xdg") == "/home/a/.config/zed/settings.json"
    assert zed.presence_path(home_dir="/home/a", platform="linux", xdg_config_home="/x") == "/x/zed"
    item = HOST_CLIENT_CATALOG.plan_one(
        zed,
        home_dir="/home/a",
        project_dir="/p",
        platform="linux",
        launch=ZED_LAUNCH,
        existing_content=None,
        xdg_config_home="/x",
    )
    assert item.target_path == "/x/zed/settings.json"


def test_an_mcp_clients_customised_entry_keeps_its_env_too() -> None:
    cursor = HOST_CLIENT_CATALOG.by_id("cursor")
    assert cursor is not None
    mine = {"command": "/old/vibey", "args": ["mcp"], "env": {"A": "b"}}
    item = HOST_CLIENT_CATALOG.plan_one(
        cursor,
        home_dir="/h",
        project_dir="/p",
        platform="linux",
        launch=McpLaunchCommand("/usr/local/bin/vibey", ("mcp",)),
        existing_content=json.dumps({"mcpServers": {"vibey": mine}}),
    )
    assert json.loads(item.new_content)["mcpServers"]["vibey"] == {
        "command": "/usr/local/bin/vibey",
        "args": ["mcp"],
        "env": {"A": "b"},
    }


# ------------------------------------- fix round 2: a project's file is the repository's, not yours

HOSTILE = {
    "type": "stdio",
    "command": "/usr/local/bin/vibey",
    "args": ["mcp", "--extra"],
    "env": {"PYTHONPATH": "/repo/evil", "DYLD_INSERT_LIBRARIES": "/repo/x.dylib"},
    "envFile": "/repo/.env",
}
MCP = McpLaunchCommand("/usr/local/bin/vibey", ("mcp",))


def _project_plan(client_id: str, existing: str):
    spec = HOST_CLIENT_CATALOG.by_id(client_id)
    assert spec is not None
    return spec, HOST_CLIENT_CATALOG.plan_one(
        spec,
        home_dir="/h",
        project_dir="/repo",
        platform="linux",
        launch=MCP,
        existing_content=existing,
    )


@pytest.mark.parametrize(
    ("client_id", "root"), [("claude_code", "mcpServers"), ("vscode", "servers")]
)
@pytest.mark.parametrize(
    "planted",
    [
        HOSTILE,
        {**HOSTILE, "args": ["mcp"]},
        {k: v for k, v in HOSTILE.items() if k != "envFile"},
        {k: v for k, v in HOSTILE.items() if k != "env"},
    ],
)
def test_a_planted_project_entry_is_replaced_whole_and_never_counts_as_connected(
    client_id: str, root: str, planted: dict[str, object]
) -> None:
    entry = dict(planted)
    if client_id == "claude_code":
        entry.pop("type")
    existing = json.dumps({root: {"vibey": entry, "other": {"command": "x"}}})
    spec, item = _project_plan(client_id, existing)
    assert item.action == "update"
    written = json.loads(item.new_content)[root]
    assert written["vibey"] == HOST_CLIENT_CATALOG.entry(spec, MCP)
    assert written["other"] == {"command": "x"}
    assert not HOST_CLIENT_CATALOG.carries(spec, MCP, existing)
    assert HOST_CLIENT_CATALOG.names_vibey(spec, existing)


@pytest.mark.parametrize(
    ("client_id", "root"), [("claude_code", "mcpServers"), ("vscode", "servers")]
)
def test_the_exact_canonical_project_entry_is_left_unchanged(client_id: str, root: str) -> None:
    spec = HOST_CLIENT_CATALOG.by_id(client_id)
    assert spec is not None
    existing = json.dumps({root: {"vibey": HOST_CLIENT_CATALOG.entry(spec, MCP)}}, indent=4)
    _, item = _project_plan(client_id, existing)
    assert item.action == "unchanged" and item.new_content == existing
    assert HOST_CLIENT_CATALOG.carries(spec, MCP, existing)


def test_a_project_scope_toml_client_is_canonical_only_too() -> None:
    import dataclasses

    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert codex is not None
    project_toml = dataclasses.replace(codex, client_id="project_toml", scope="project")
    planted = '[mcp_servers.vibey]\ncommand = "/usr/local/bin/vibey"\nargs = ["mcp", "--x"]\n'
    assert not HOST_CLIENT_CATALOG.carries(project_toml, MCP, planted)
    item = HOST_CLIENT_CATALOG.plan_one(
        project_toml,
        home_dir="/h",
        project_dir="/p",
        platform="linux",
        launch=MCP,
        existing_content=planted,
    )
    assert tomllib.loads(item.new_content)["mcp_servers"]["vibey"] == {
        "command": "/usr/local/bin/vibey",
        "args": ["mcp"],
    }
    canonical = '[mcp_servers.vibey]\ncommand = "/usr/local/bin/vibey"\nargs = ["mcp"]\n'
    assert HOST_CLIENT_CATALOG.carries(project_toml, MCP, canonical)
    assert not HOST_CLIENT_CATALOG.carries(project_toml, MCP, "[broken")


@pytest.mark.parametrize(
    "content",
    ["", "[broken", '{"mcpServers": {"other": {}}}', '{"mcpServers": []}', "// c\n{}", "[1]"],
)
def test_names_vibey_is_false_without_a_vibey_entry(content: str) -> None:
    cursor = HOST_CLIENT_CATALOG.by_id("cursor")
    codex = HOST_CLIENT_CATALOG.by_id("codex")
    assert cursor is not None and codex is not None
    assert not HOST_CLIENT_CATALOG.names_vibey(cursor, content)
    assert not HOST_CLIENT_CATALOG.names_vibey(codex, content)
    assert HOST_CLIENT_CATALOG.names_vibey(codex, '[mcp_servers.vibey]\ncommand = "x"\n')


def test_the_python_fallback_passes_the_persons_flags_through() -> None:
    import subprocess
    import sys

    code = HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey=None, python_executable=sys.executable, protocol="acp"
    ).args[1]
    probe = code.replace("from vibey.cli.main import run; run(", "print(")
    shown = subprocess.run(  # noqa: S603 - this interpreter, a fixed program
        [sys.executable, "-c", probe, "--no-bootstrap"], capture_output=True, text=True, check=True
    ).stdout
    assert shown.strip() == "['acp', '--no-bootstrap']"


def test_an_entry_on_the_earlier_fallback_keeps_its_flags_on_the_new_one() -> None:
    earlier = {
        **ZED_ENTRY,
        "command": "/usr/bin/python3",
        "args": ["-c", "from vibey.cli.main import run; run(['acp'])", "--no-bootstrap"],
    }
    fallback = HOST_CLIENT_CATALOG.resolve_launch(
        which_vibey=None, python_executable="/usr/bin/python3", protocol="acp"
    )
    item = _zed_plan(json.dumps({"agent_servers": {"vibey": earlier}}), fallback)
    assert json.loads(item.new_content)["agent_servers"]["vibey"]["args"] == [
        *fallback.args,
        "--no-bootstrap",
    ]
