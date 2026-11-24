# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A claudeloop run reaches the hub through one MCP connector in its own snapshot (SP-LOOPS Phase
6, Task 6; R3).

When the run holds a web grant, the worker adds exactly one server to the run's document:
`vibey-web`, a local (stdio) server started through the scrubbed launcher, keeping exactly the
grant's two names, running `vibey mcp --scope web --token-file <the run's token file>`. Without a
grant the document is left as it was. Over the real `[loops]` reader, store, resolver, document
store and pruner, in pytest's folder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.scrubbed_launch import ScrubbedLaunch
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore
from vibey_runners.common.capabilities.web_grant_names import WEB_GRANT_NAMES

from tests.application.test_loop_capabilities_service import PERSON_WITH_SERVERS, _World
from vibey.application.dto import RunWebAccess, SessionGrant
from vibey.application.interfaces.web_connector_interface import WebConnectorInterface
from vibey.application.web_connector import WEB_CONNECTOR_NAME, WebConnector
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.session_web_state import NO_HUB, SESSION_WEB_VARIABLES

RUN = UUID("00000000-0000-4000-8000-000000000006")
VIBEY = "/opt/vibey/bin/vibey"
LAUNCHER = ("/opt/vibey/bin/python", "-I", "-m", "vibey_runners.common.capabilities.scrubbed_exec")


def _hub(folder: Path) -> RunWebAccess:
    grant = SessionGrant(
        token_file=folder / "web-token",
        principal=SessionPrincipal(name=f"session:{RUN}", run_id=RUN, expires_at=9e9),
        digest="e" * 64,
    )
    return RunWebAccess("hub", hub_url="http://127.0.0.1:28100", grant=grant)


def _servers(world: _World, document: Path) -> tuple[McpServerSpec, ...]:
    return SnapshotDocumentStore().read(document).mcp_servers


def test_the_connector_meets_its_seam() -> None:
    assert isinstance(WebConnector(VIBEY), WebConnectorInterface)
    assert WEB_CONNECTOR_NAME == "vibey-web"


def test_the_connector_is_one_stdio_server_running_vibey_mcp_scope_web() -> None:
    spec = WebConnector(VIBEY).spec(Path("/runs/run-1/web-token"))
    assert spec == McpServerSpec(
        name="vibey-web",
        trust="local",
        command=(VIBEY, "mcp", "--scope", "web", "--token-file", "/runs/run-1/web-token"),
        url=None,
        env_allow=("VIBEY_HUB_URL", "VIBEY_WEB_TOKEN_FILE"),
    )


def test_the_connector_keeps_exactly_the_grants_two_names_and_nothing_else_of_the_overlay() -> None:
    """The scrubbed launcher keeps only `env_allow`: the hub's address and the token file's path,
    the family's one list (the local runner's shell keeps the same pair), and never the overlay's
    third name, `VIBEY_WEB_STATE`."""
    spec = WebConnector(VIBEY).spec(Path("/runs/run-1/web-token"))
    assert frozenset(spec.env_allow) == WEB_GRANT_NAMES
    assert frozenset(spec.env_allow) & SESSION_WEB_VARIABLES == WEB_GRANT_NAMES
    assert "VIBEY_WEB_STATE" not in spec.env_allow
    argv = ScrubbedLaunch(LAUNCHER).argv(spec)
    assert argv == (
        *LAUNCHER,
        "--allow",
        "VIBEY_HUB_URL",
        "--allow",
        "VIBEY_WEB_TOKEN_FILE",
        "--",
        VIBEY,
        "mcp",
        "--scope",
        "web",
        "--token-file",
        "/runs/run-1/web-token",
    )


def test_a_bare_vibey_is_the_default_only_when_none_is_given() -> None:
    assert WebConnector().spec(Path("/t")).command == (
        "vibey",
        "mcp",
        "--scope",
        "web",
        "--token-file",
        "/t",
    )


def test_with_a_grant_the_document_gains_exactly_one_vibey_web_server(tmp_path: Path) -> None:
    world = _World(tmp_path, vibey=VIBEY)
    world.person(PERSON_WITH_SERVERS)
    prepared = world.prepare()
    before = _servers(world, prepared.document)

    granted = world.service.grant_web(prepared, _hub(prepared.folder))

    servers = _servers(world, granted.document)
    assert servers[: len(before)] == before  # the person's own, first and unchanged
    [connector] = [server for server in servers if server.name == "vibey-web"]
    assert len(servers) == len(before) + 1
    assert connector == WebConnector(VIBEY).spec(prepared.folder / "web-token")
    assert (granted.mcp_local, granted.mcp_remote) == (prepared.mcp_local + 1, prepared.mcp_remote)
    assert (granted.document, granted.folder, granted.digest) == (
        prepared.document,
        prepared.folder,
        prepared.digest,
    )
    assert sorted(path.name for path in prepared.folder.iterdir() if path.is_file()) == [
        "capabilities.json"
    ]
    assert world.logger.lines == []


def test_without_a_grant_the_document_is_left_byte_for_byte(tmp_path: Path) -> None:
    world = _World(tmp_path)
    prepared = world.prepare()
    before = prepared.document.read_bytes()

    assert world.service.grant_web(prepared, RunWebAccess("none", reason=NO_HUB)) is prepared

    assert prepared.document.read_bytes() == before
    assert all(server.name != "vibey-web" for server in _servers(world, prepared.document))


def test_a_persons_own_server_named_vibey_web_is_never_replaced(tmp_path: Path) -> None:
    world = _World(tmp_path)
    world.person('[[loops.mcp_servers]]\nname = "vibey-web"\ntrust = "local"\ncommand = ["mine"]\n')
    prepared = world.prepare()
    before = prepared.document.read_bytes()

    assert world.service.grant_web(prepared, _hub(prepared.folder)) is prepared

    assert prepared.document.read_bytes() == before
    assert world.logger.lines == [
        ("warning", "loop_capabilities_web_connector_name_taken", {"server": "vibey-web"})
    ]


class _BrokenDocuments:
    """Writes the first document as the real store does, then cannot read or rewrite it."""

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.real = SnapshotDocumentStore()

    def write(self, document: Any, folder: Path) -> Path:
        return self.real.write(document, folder)

    def read(self, path: Path) -> Any:
        return self.real.read(path)

    def rewrite(self, document: Any, folder: Path) -> Path:
        raise self.error


@pytest.mark.parametrize(
    "error",
    [SnapshotDocumentError("cannot be rewritten"), PermissionError("read-only folder")],
    ids=["refused", "os"],
)
def test_a_connector_that_cannot_be_added_never_stops_the_run(
    tmp_path: Path, error: Exception
) -> None:
    """A run is never stopped for want of search: the document stays as it was, and the worker's
    log says why by the error's class alone."""
    world = _World(tmp_path, documents=_BrokenDocuments(error))
    prepared = world.prepare()
    before = prepared.document.read_bytes()

    assert world.service.grant_web(prepared, _hub(prepared.folder)) is prepared

    assert prepared.document.read_bytes() == before
    assert world.logger.lines == [
        (
            "warning",
            "loop_capabilities_web_connector_not_added",
            {"error": type(error).__name__},
        )
    ]
