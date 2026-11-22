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
    # The web tools' rule (ADR-0102): their results are data, and a query or URL leaves the machine.
    assert "vibey_search" in HOST_INSTRUCTIONS and "vibey_fetch" in HOST_INSTRUCTIONS
    assert "never put secrets" in HOST_INSTRUCTIONS


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
        "vibey_search",
        "vibey_fetch",
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


def test_the_web_tools_need_the_web_scope_and_say_their_results_are_untrusted_data() -> None:
    """ADR-0102: a principal without `web` is never offered them, and each description tells the
    model that what comes back is data, never instructions, and that what it sends leaves."""
    without_web = HOST_TOOL_CATALOG.for_scopes(AGENT_DEFAULT_SCOPES - {HubScope.WEB})
    assert not {"vibey_search", "vibey_fetch"} & {tool.name for tool in without_web}
    only_web = HOST_TOOL_CATALOG.for_scopes(frozenset({HubScope.WEB}))
    assert [tool.name for tool in only_web] == ["vibey_search", "vibey_fetch"]
    by_name = {d["name"]: d for d in HOST_TOOL_CATALOG.mcp_definitions(AGENT_DEFAULT_SCOPES)}
    for name, route in (
        ("vibey_search", "/api/v1/web/search"),
        ("vibey_fetch", "/api/v1/web/fetch"),
    ):
        definition = by_name[name]
        description = definition["description"]
        assert "UNTRUSTED" in description and "never follow" in description
        assert "leaves this computer" in description and "recorded" in description
        assert definition["annotations"]["openWorldHint"] is True
        assert definition["annotations"]["destructiveHint"] is False
        tool = HOST_TOOL_CATALOG.by_name(name)
        assert tool is not None and tool.route == route and tool.method == "POST"
    # Every other tool stays inside vibey.
    assert all(
        d["annotations"]["openWorldHint"] is False
        for n, d in by_name.items()
        if n not in {"vibey_search", "vibey_fetch"}
    )


def test_the_web_tools_input_schemas_are_bounded() -> None:
    by_name = {d["name"]: d for d in HOST_TOOL_CATALOG.mcp_definitions(AGENT_DEFAULT_SCOPES)}
    search = by_name["vibey_search"]["inputSchema"]
    assert search["required"] == ["query"]
    assert search["properties"]["query"]["maxLength"] == 512
    assert (search["properties"]["limit"]["minimum"], search["properties"]["limit"]["maximum"]) == (
        1,
        20,
    )
    assert search["properties"]["project_id"]["format"] == "uuid"
    assert search["additionalProperties"] is False
    fetch = by_name["vibey_fetch"]["inputSchema"]
    assert fetch["required"] == ["url"]
    assert fetch["properties"]["url"]["maxLength"] == 2048
    assert set(fetch["properties"]) == {"url", "project_id"}


def test_a_search_or_fetch_becomes_one_bounded_hub_request() -> None:
    search = HOST_TOOL_CATALOG.build_call(
        "vibey_search", {"query": "asyncpg pool", "limit": 3}, request_id="r"
    )
    assert (search.method, search.route, search.query) == ("POST", "/api/v1/web/search", ())
    assert search.body == {"query": "asyncpg pool", "limit": 3}
    fetch = HOST_TOOL_CATALOG.build_call(
        "vibey_fetch",
        {"url": "https://docs.example/", "project_id": UPPER_UUID},
        request_id="r",
    )
    assert fetch.body == {"url": "https://docs.example/", "project_id": UPPER_UUID.lower()}
    for name, arguments in (
        ("vibey_search", {"query": "x" * 513}),
        ("vibey_search", {"query": "  "}),
        ("vibey_search", {"query": "q", "limit": 21}),
        ("vibey_search", {"query": "q", "headers": {"Cookie": "a"}}),
        ("vibey_fetch", {"url": "https://a.example/" + "a" * 2048}),
        ("vibey_fetch", {"url": "https://a.example/", "method": "POST"}),
        ("vibey_fetch", {}),
    ):
        with pytest.raises(HostToolError):
            HOST_TOOL_CATALOG.build_call(name, arguments, request_id="r")


def test_a_search_is_a_read_to_a_session_mode_and_a_fetch_is_not() -> None:
    """ADR-0102: the scope a session's mode must hold (`session_scope`) is `view` for a search,
    `web` itself for a fetch, and the tool's own scope for every other tool."""
    search = HOST_TOOL_CATALOG.by_name("vibey_search")
    fetch = HOST_TOOL_CATALOG.by_name("vibey_fetch")
    assert search is not None and fetch is not None
    assert (search.scope, search.session_scope) == (HubScope.WEB, HubScope.VIEW)
    assert (fetch.scope, fetch.session_scope) == (HubScope.WEB, HubScope.WEB)
    for tool in HOST_TOOL_CATALOG.all():
        if tool.name not in {"vibey_search", "vibey_fetch"}:
            assert tool.session_scope == tool.scope
