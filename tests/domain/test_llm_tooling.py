# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which LLM-facing surface each client has, and the command for one it lacks (SP-ACP)."""

from __future__ import annotations

import pytest

from vibey.domain.host_clients import HOST_CLIENT_CATALOG, HostClientSpec
from vibey.domain.interfaces.llm_tooling_interface import LlmToolingInterface
from vibey.domain.llm_tooling import (
    LLM_TOOLING,
    PLUGIN_COMMANDS,
    SURFACES,
    ClientTooling,
    ToolingFinding,
)


def spec(client_id: str) -> HostClientSpec:
    found = HOST_CLIENT_CATALOG.by_id(client_id)
    assert found is not None
    return found


def states(client_id: str, found: ClientTooling) -> dict[str, tuple[str, str]]:
    return {f.surface: (f.state, f.detail) for f in LLM_TOOLING.findings(spec(client_id), found)}


NOTHING = ClientTooling(entry="missing", entry_detail="no vibey entry in ~/x")


def test_the_catalogue_honours_its_interface_and_reports_four_surfaces_in_order() -> None:
    assert isinstance(LLM_TOOLING, LlmToolingInterface)
    found = LLM_TOOLING.findings(spec("cursor"), NOTHING)
    assert tuple(f.surface for f in found) == SURFACES
    assert [f.name for f in found] == [f"cursor:{s}" for s in SURFACES]


def test_zed_has_the_acp_agent_entry_and_nothing_else_applies() -> None:
    got = states("zed", ClientTooling(entry="present", entry_detail="in ~/.config/zed"))
    assert got["acp-agent"] == ("present", "in ~/.config/zed")
    assert got["mcp-server"][0] == "not-applicable" and "over ACP" in got["mcp-server"][1]
    assert got["skill"][0] == "not-applicable"
    assert got["plugin"][0] == "not-applicable"


def test_a_missing_entry_names_the_connect_command_for_that_client() -> None:
    got = states("zed", ClientTooling(entry="missing", entry_detail="no vibey entry in ~/s"))
    assert got["acp-agent"] == (
        "missing",
        "no vibey entry in ~/s; run `vibey connect --client zed`",
    )


def test_a_refused_entry_carries_its_reason_and_snippet_and_not_the_connect_command() -> None:
    refused = ClientTooling(entry="refused", entry_detail='not strict JSON: "agent_servers": {}')
    state, detail = states("zed", refused)["acp-agent"]
    assert state == "missing"
    assert detail == 'not strict JSON: "agent_servers": {}'
    assert "vibey connect" not in detail


def test_an_mcp_client_has_the_mcp_entry_and_no_acp_entry() -> None:
    got = states("codex", ClientTooling(entry="present", entry_detail="in ~/.codex/config.toml"))
    assert got["mcp-server"] == ("present", "in ~/.codex/config.toml")
    assert got["acp-agent"][0] == "not-applicable" and "over MCP" in got["acp-agent"][1]


def test_claude_code_gets_its_server_and_skill_through_the_plugin() -> None:
    got = states("claude_code", ClientTooling("missing", "no ./.mcp.json", plugin_installed=True))
    assert got["mcp-server"] == ("present", "through the plugin vibey@vibey")
    assert got["skill"] == ("present", "vibey-chat-driver in the plugin vibey@vibey")
    assert got["plugin"] == ("present", "vibey@vibey installed")


def test_claude_code_without_the_plugin_is_told_the_marketplace_commands() -> None:
    got = states("claude_code", NOTHING)
    assert got["plugin"] == ("missing", PLUGIN_COMMANDS)
    assert got["skill"] == ("missing", f"vibey-chat-driver: {PLUGIN_COMMANDS}")
    assert got["mcp-server"][0] == "missing"
    assert "/plugin install vibey@vibey" in PLUGIN_COMMANDS
    assert "/plugin marketplace add the-vibey-project/vibey" in PLUGIN_COMMANDS


def test_a_skill_found_in_its_folder_is_present() -> None:
    found = ClientTooling("missing", "x", skill_at="~/.claude/skills/vibey-chat-driver")
    assert states("claude_code", found)["skill"] == (
        "present",
        "~/.claude/skills/vibey-chat-driver",
    )


def test_codex_is_told_the_exact_copy_command_for_its_skill() -> None:
    found = ClientTooling("present", "in ~/.codex/config.toml", skill_install="cp -R a b")
    assert states("codex", found)["skill"] == ("missing", "vibey-chat-driver: cp -R a b")
    assert states("codex", found)["plugin"][0] == "not-applicable"


@pytest.mark.parametrize("client_id", ["claude_desktop", "cursor", "vscode", "gemini_cli", "zed"])
def test_clients_without_a_skill_folder_or_plugin_say_not_applicable(client_id: str) -> None:
    got = states(client_id, NOTHING)
    assert got["skill"][0] == "not-applicable"
    assert got["plugin"][0] == "not-applicable"


def test_each_state_is_marked_as_doctor_marks_it_and_missing_never_fails() -> None:
    marks = {
        state: ToolingFinding("c", "skill", state, "").mark
        for state in ("present", "missing", "not-applicable")
    }
    assert marks == {"present": "PASS", "missing": "WARN", "not-applicable": "UNKNOWN"}
