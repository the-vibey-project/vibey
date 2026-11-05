# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the pure host-LLM tool catalogue and call builder (ADR-0100)."""

from typing import Any

import pytest

from vibey.domain.host_tools import (
    HOST_INSTRUCTIONS,
    HOST_TOOL_CATALOG,
    HOST_TOOLS,
    HostToolError,
    HostTools,
)
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface

SAMPLE_UUID = "12345678-1234-5678-1234-567812345678"
UPPER_UUID = "12345678-1234-5678-1234-56781234ABCD"


def test_the_catalogue_satisfies_its_interface() -> None:
    assert isinstance(HOST_TOOL_CATALOG, HostToolsInterface)
    assert HOST_TOOL_CATALOG.all() == HOST_TOOLS
    assert "untrusted DATA" in HOST_INSTRUCTIONS
    assert "dry_run=true" in HOST_INSTRUCTIONS


def test_every_tool_stays_inside_the_agent_default_ceiling_and_never_bumps_or_spends() -> None:
    names = [tool.name for tool in HOST_TOOL_CATALOG.all()]
    assert names == [
        "vibey_projects",
        "vibey_status",
        "vibey_gates",
        "vibey_answer_gate",
        "vibey_budget",
        "vibey_queue",
        "vibey_ledger",
        "vibey_loops",
        "vibey_lanes",
        "vibey_doctor",
        "vibey_start_project",
        "vibey_start_work",
        "vibey_pause_work",
        "vibey_abandon_project",
    ]
    for tool in HOST_TOOL_CATALOG.all():
        assert tool.scope in AGENT_DEFAULT_SCOPES
        assert tool.scope not in {HubScope.SPEND, HubScope.BUMP, HubScope.WORKFLOWS}


def test_tools_filter_by_granted_scopes_and_render_mcp_annotations() -> None:
    view_only = HOST_TOOL_CATALOG.for_scopes(frozenset({HubScope.VIEW}))
    assert all(tool.scope == HubScope.VIEW for tool in view_only)
    assert {tool.name for tool in view_only} == {
        "vibey_projects",
        "vibey_status",
        "vibey_gates",
        "vibey_budget",
        "vibey_queue",
        "vibey_ledger",
        "vibey_loops",
        "vibey_lanes",
        "vibey_doctor",
    }
    definitions = HOST_TOOL_CATALOG.mcp_definitions(AGENT_DEFAULT_SCOPES)
    assert len(definitions) == len(HOST_TOOLS)
    by_name = {d["name"]: d for d in definitions}
    abandon = by_name["vibey_abandon_project"]
    assert abandon["annotations"]["destructiveHint"] is True
    assert abandon["annotations"]["readOnlyHint"] is False
    assert abandon["annotations"]["openWorldHint"] is False
    assert abandon["inputSchema"]["properties"]["dry_run"]["default"] is True
    projects = by_name["vibey_projects"]
    assert "required" not in projects["inputSchema"]
    assert projects["annotations"]["readOnlyHint"] is True


def test_build_call_for_parameterless_and_path_routes() -> None:
    projects = HOST_TOOL_CATALOG.build_call("vibey_projects", None, request_id="req-1")
    assert projects.method == "GET"
    assert projects.route == "/api/v1/projects"
    assert projects.query == ()
    assert projects.body is None
    assert HOST_TOOL_CATALOG.format_query(projects.query) == ""

    status = HOST_TOOL_CATALOG.build_call(
        "vibey_status", {"project_id": UPPER_UUID}, request_id="req-2"
    )
    assert status.route == f"/api/v1/projects/{UPPER_UUID.lower()}/status"


def test_build_call_for_gates_with_and_without_project_filter() -> None:
    all_gates = HOST_TOOL_CATALOG.build_call("vibey_gates", {}, request_id="req-1")
    assert all_gates.route == "/api/v1/gates"
    assert all_gates.query == ()

    filtered = HOST_TOOL_CATALOG.build_call(
        "vibey_gates", {"project_id": SAMPLE_UUID}, request_id="req-2"
    )
    assert filtered.query == (("project_id", SAMPLE_UUID),)
    assert HOST_TOOL_CATALOG.format_query(filtered.query) == f"?project_id={SAMPLE_UUID}"


def test_build_call_for_answer_gate_injects_request_id() -> None:
    call = HOST_TOOL_CATALOG.build_call(
        "vibey_answer_gate",
        {"gate_id": SAMPLE_UUID, "answer": {"verdict": "accept"}},
        request_id="mcp-req-9",
    )
    assert call.method == "POST"
    assert call.route == f"/api/v1/gates/{SAMPLE_UUID}/answer"
    assert call.body == {"answer": {"verdict": "accept"}, "request_id": "mcp-req-9"}


def test_build_call_for_ledger_queries_and_defaults() -> None:
    default_call = HOST_TOOL_CATALOG.build_call(
        "vibey_ledger", {"project_id": SAMPLE_UUID}, request_id="req-1"
    )
    assert default_call.query == (("limit", "50"),)

    full_call = HOST_TOOL_CATALOG.build_call(
        "vibey_ledger",
        {
            "project_id": SAMPLE_UUID,
            "text": "handoff",
            "kind": ["GateRaised", "GateAnswered"],
            "actor": "host",
            "limit": 25,
        },
        request_id="req-2",
    )
    assert full_call.query == (
        ("text", "handoff"),
        ("kind", "GateRaised"),
        ("kind", "GateAnswered"),
        ("actor", "host"),
        ("limit", "25"),
    )


def test_build_call_for_project_lifecycle_tools() -> None:
    start = HOST_TOOL_CATALOG.build_call(
        "vibey_start_project", {"name": "demo"}, request_id="req-1"
    )
    assert start.method == "POST"
    assert start.route == "/api/v1/projects"
    assert start.body == {"name": "demo", "intake": ""}

    work = HOST_TOOL_CATALOG.build_call(
        "vibey_start_work", {"project_id": SAMPLE_UUID}, request_id="req-2"
    )
    assert work.method == "POST"
    assert work.route == f"/api/v1/projects/{SAMPLE_UUID}/work/start"
    assert work.body is None

    abandon_default = HOST_TOOL_CATALOG.build_call(
        "vibey_abandon_project",
        {"project_id": SAMPLE_UUID, "reason": "superseded"},
        request_id="req-3",
    )
    assert abandon_default.body == {"reason": "superseded", "dry_run": True}

    abandon_live = HOST_TOOL_CATALOG.build_call(
        "vibey_abandon_project",
        {"project_id": SAMPLE_UUID, "reason": "superseded", "dry_run": False},
        request_id="req-4",
    )
    assert abandon_live.body == {"reason": "superseded", "dry_run": False}


@pytest.mark.parametrize(
    ("name", "arguments", "request_id", "match"),
    [
        ("vibey_nonexistent", {}, "req-1", "unknown tool 'vibey_nonexistent'"),
        ("vibey_projects", {}, "   ", "request_id must not be empty"),
        ("vibey_projects", ["not-a-dict"], "req-1", "tool arguments must be a JSON object"),
        ("vibey_projects", {"extra": 1}, "req-1", "unknown argument\\(s\\): extra"),
        ("vibey_status", {}, "req-1", "missing required argument 'project_id'"),
        ("vibey_status", {"project_id": "../etc/passwd"}, "req-1", "must be a canonical UUID"),
        ("vibey_status", {"project_id": 123}, "req-1", "must be a canonical UUID"),
        ("vibey_start_project", {"name": 42}, "req-1", "must be a string"),
        ("vibey_start_project", {"name": "   "}, "req-1", "must not be blank"),
        ("vibey_start_project", {"name": "x" * 200}, "req-1", "exceeds maximum length"),
        (
            "vibey_ledger",
            {"project_id": SAMPLE_UUID, "kind": "GateRaised"},
            "req-1",
            "must be a list of strings",
        ),
        (
            "vibey_ledger",
            {"project_id": SAMPLE_UUID, "kind": ["  "]},
            "req-1",
            "entries must be non-empty strings",
        ),
        (
            "vibey_ledger",
            {"project_id": SAMPLE_UUID, "limit": True},
            "req-1",
            "must be an integer",
        ),
        (
            "vibey_ledger",
            {"project_id": SAMPLE_UUID, "limit": 0},
            "req-1",
            "must be between 1 and 200",
        ),
        (
            "vibey_ledger",
            {"project_id": SAMPLE_UUID, "limit": 201},
            "req-1",
            "must be between 1 and 200",
        ),
        (
            "vibey_abandon_project",
            {"project_id": SAMPLE_UUID, "reason": "done", "dry_run": "yes"},
            "req-1",
            "must be a boolean",
        ),
        (
            "vibey_answer_gate",
            {"gate_id": SAMPLE_UUID, "answer": {}},
            "req-1",
            "must be a non-empty JSON object",
        ),
        (
            "vibey_answer_gate",
            {"gate_id": SAMPLE_UUID, "answer": "yes"},
            "req-1",
            "must be a non-empty JSON object",
        ),
    ],
)
def test_build_call_rejects_invalid_inputs(
    name: str, arguments: Any, request_id: str, match: str
) -> None:
    with pytest.raises(HostToolError, match=match):
        HostTools().build_call(name, arguments, request_id=request_id)


def test_truncate_preserves_short_responses_and_marks_long_ones_explicitly() -> None:
    assert HOST_TOOL_CATALOG.truncate("hello", limit=10) == "hello"
    assert HOST_TOOL_CATALOG.truncate("0123456789", limit=10) == "0123456789"
    truncated = HOST_TOOL_CATALOG.truncate("0123456789abcdef", limit=10)
    assert truncated == "0123456789\n...[truncated 6 chars]"
