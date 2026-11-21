# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP server's bytes are what they were before the JSON-RPC codec was shared (SP-ACP Task 1).

`golden/mcp_transcript.jsonl` was captured from `McpStdioServer` before the refactor, one record
per input line: which server configuration answered, the input, and the exact output. The release
number is not behaviour, so the transcript holds a placeholder where `serverInfo.version` is.

Module-level test functions rather than a class with an interface beside it (ADR-0016): pytest
collects functions, and the fixtures here are data.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from vibey import __version__
from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.infrastructure.mcp.hub_gateway import (
    HubGatewayError,
    HubGatewayResponse,
)
from vibey.infrastructure.mcp.stdio_server import MCP_STDIO_SERVER, McpStdioServer

GOLDEN = Path(__file__).parent / "golden" / "mcp_transcript.jsonl"
_OK = HubGatewayResponse(200, '[{"id":"1"}]', True)


class _StubGateway:
    def __init__(
        self,
        scopes: frozenset[HubScope],
        response: HubGatewayResponse,
        error: HubGatewayError | None = None,
    ) -> None:
        self._scopes = scopes
        self._response = response
        self._error = error

    def agent_scopes(self) -> frozenset[HubScope]:
        return self._scopes

    def call(self, call: HubCall) -> HubGatewayResponse:
        if self._error is not None:
            raise self._error
        return self._response


@dataclass(frozen=True)
class _Case:
    config: str
    input: str
    output: str | None
    serve: bool


def _server(config: str) -> McpStdioServer:
    fixed = lambda: "req-fixed"  # noqa: E731 - a one-line stub id factory
    gateways = {
        "default": _StubGateway(AGENT_DEFAULT_SCOPES, _OK),
        "view": _StubGateway(frozenset({HubScope.VIEW}), _OK),
        "truncate": _StubGateway(
            frozenset({HubScope.VIEW}), HubGatewayResponse(200, '{"projects": []}', True)
        ),
        "refused": _StubGateway(
            AGENT_DEFAULT_SCOPES, HubGatewayResponse(403, '{"detail":"forbidden"}', False)
        ),
        "error": _StubGateway(AGENT_DEFAULT_SCOPES, _OK, HubGatewayError("no hub")),
    }
    limit = {"max_response_chars": 12} if config == "truncate" else {}
    return McpStdioServer(gateway=gateways[config], request_id_factory=fixed, **limit)


def _golden_cases() -> list[_Case]:
    cases = []
    for raw in GOLDEN.read_text(encoding="utf-8").splitlines():
        record = json.loads(raw)
        output = record["output"]
        if output is not None:
            output = output.replace("@@VERSION@@", __version__)
        cases.append(_Case(record["config"], record["input"], output, record.get("serve", False)))
    return cases


def test_the_golden_transcript_covers_every_branch_it_claims() -> None:
    cases = _golden_cases()
    assert len(cases) >= 40
    assert {c.config for c in cases} == {"default", "view", "truncate", "refused", "error"}
    assert any(c.output is None for c in cases)  # notifications and blank lines
    assert any(c.serve for c in cases)


def test_mcp_replies_are_byte_identical_to_the_golden_transcript() -> None:
    for case in _golden_cases():
        server = _server(case.config)
        if case.serve:
            out = io.StringIO()
            server.serve(io.StringIO(case.input), out)
            assert out.getvalue() == case.output, case.input
        else:
            assert server.handle_line(case.input) == case.output, case.input


@pytest.mark.parametrize("version", ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"])
def test_the_production_singleton_negotiates_every_supported_protocol(version: str) -> None:
    line = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": version}}
    )
    reply = MCP_STDIO_SERVER.handle_line(line)
    assert reply is not None
    assert json.loads(reply)["result"]["protocolVersion"] == version
