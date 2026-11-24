# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""infrastructure/capabilities/snapshot_applier.py — a run's capability document, read strictly
and turned into what one claudeloop session is given (SP-LOOPS Phase 4, Task 4; R4, R9, R11,
R12; Review Focus 5)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest
from vibey_runners.common.capabilities.instruction_files import InstructionFileReader
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

from claudeloop.domain.capabilities import CLAUDE_BUILTIN_WEB_TOOLS, AppliedCapabilities
from claudeloop.domain.errors import CapabilityFlagConflict, CapabilitySnapshotRefused
from claudeloop.domain.mcp_config import McpConfigTranslator
from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
from claudeloop.infrastructure.interfaces import CapabilitySnapshotApplierInterface
from tests.capability_documents import DIGEST, CapabilityDocumentWriter

SENTINEL = "SENTINEL-VALUE-7731"
LAUNCHER = ("/usr/bin/python3", "-m", "vibey_runners.common.capabilities.scrubbed_exec")


class _RecordingLogger:
    """An `application.ports.Logger` that keeps every call, so a test can read what was said."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _RecordingLogger:
        del kwargs
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.calls.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.calls.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.calls.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.calls.append(("error", event, kwargs))


def _applier(
    *,
    local_backend: bool = False,
    environ: Mapping[str, str] | None = None,
    logger: _RecordingLogger | None = None,
) -> CapabilitySnapshotApplier:
    return CapabilitySnapshotApplier(
        SnapshotDocumentStore(),
        local_backend=local_backend,
        mcp=McpConfigTranslator(LAUNCHER),
        environ=environ if environ is not None else {},
        logger=logger if logger is not None else _RecordingLogger(),
        instructions=InstructionFileReader(),
    )


def _files(*env_allow: str) -> McpServerSpec:
    return McpServerSpec(
        name="files",
        trust="local",
        command=("files-server", "--root", "."),
        url=None,
        env_allow=env_allow,
    )


def _docs() -> McpServerSpec:
    return McpServerSpec(
        name="docs",
        trust="remote",
        command=None,
        url="https://docs.example.invalid/mcp",
        env_allow=(),
    )


def test_the_applier_satisfies_its_interface() -> None:
    assert isinstance(_applier(), CapabilitySnapshotApplierInterface)


def test_builtin_web_false_disallows_websearch_and_webfetch(tmp_path: Path) -> None:
    writer = CapabilityDocumentWriter(tmp_path)
    inputs = Path("/inputs/one")
    path = writer.write(builtin_web=False, folders=[inputs])
    applied = _applier().load(path, cwd=tmp_path)
    assert applied == AppliedCapabilities(
        digest=DIGEST,
        plugin_dirs=(str(writer.run / "plugins" / "alpha"), str(writer.run / "plugins" / "beta")),
        skills=("alpha:review", "beta:ship"),
        mcp_servers={},
        disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS,
        add_dirs=(str(inputs),),
        system_prompt_append="",
        notices=(),
    )


def test_builtin_web_true_leaves_the_web_tools_on_an_anthropic_backend(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(builtin_web=True)
    applied = _applier().load(path, cwd=tmp_path)
    assert applied.disallowed_tools == ()
    assert applied.notices == ()


def test_a_local_backend_disallows_them_even_when_builtin_web_is_true_and_says_so(
    tmp_path: Path,
) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(builtin_web=True)
    applied = _applier(local_backend=True).load(path, cwd=tmp_path)
    assert applied.disallowed_tools == CLAUDE_BUILTIN_WEB_TOOLS
    assert len(applied.notices) == 1
    assert "builtin_web" in applied.notices[0]
    assert "local backend" in applied.notices[0]


def test_a_local_backend_with_builtin_web_false_has_nothing_to_say(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(builtin_web=False)
    applied = _applier(local_backend=True).load(path, cwd=tmp_path)
    assert applied.disallowed_tools == CLAUDE_BUILTIN_WEB_TOOLS
    assert applied.notices == ()


def test_a_refused_document_raises_capability_snapshot_refused_naming_only_the_path(
    tmp_path: Path,
) -> None:
    path = CapabilityDocumentWriter(tmp_path).write()
    document = json.loads(path.read_text(encoding="utf-8"))
    document["version"] = SENTINEL
    document[SENTINEL] = SENTINEL
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CapabilitySnapshotRefused) as caught:
        _applier().load(path, cwd=tmp_path)
    message = str(caught.value)
    assert str(path) in message
    assert SENTINEL not in message
    assert SENTINEL not in caught.value.reason


def test_a_missing_document_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "gone" / "capabilities.json"
    with pytest.raises(CapabilitySnapshotRefused, match="refused"):
        _applier().load(path, cwd=tmp_path)


class _UnreadableStore:
    def write(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        raise AssertionError("never written here")

    def rewrite(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        raise AssertionError("never rewritten here")

    def read(self, path: Path) -> SnapshotDocumentInterface:
        raise OSError(f"cannot read {SENTINEL}")


def test_an_os_error_while_reading_is_refused_without_its_text(tmp_path: Path) -> None:
    path = tmp_path / "capabilities.json"
    applier = CapabilitySnapshotApplier(
        _UnreadableStore(),
        local_backend=False,
        mcp=McpConfigTranslator(LAUNCHER),
        environ={},
        logger=_RecordingLogger(),
        instructions=InstructionFileReader(),
    )
    with pytest.raises(CapabilitySnapshotRefused) as caught:
        applier.load(path, cwd=tmp_path)
    assert str(path) in str(caught.value)
    assert SENTINEL not in str(caught.value)


def _with_server(name: str) -> AppliedCapabilities:
    return AppliedCapabilities(
        digest=DIGEST,
        plugin_dirs=(),
        skills=(),
        mcp_servers={name: {"type": "http", "url": "https://example.invalid/mcp"}},
        disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS,
        add_dirs=(),
        system_prompt_append="",
        notices=(),
    )


def test_a_connector_named_like_a_snapshot_server_is_a_conflict() -> None:
    with pytest.raises(CapabilityFlagConflict, match="'docs'"):
        _applier().check_flags(_with_server("docs"), connectors=["other", "docs"], web_search=False)


def test_web_search_with_the_web_tools_off_is_a_conflict() -> None:
    with pytest.raises(CapabilityFlagConflict, match="--web-search"):
        _applier().check_flags(_with_server("docs"), connectors=[], web_search=True)


def test_flags_that_add_to_the_snapshot_are_accepted() -> None:
    applied = _with_server("docs")
    _applier().check_flags(applied, connectors=["other"], web_search=False)
    allowed = AppliedCapabilities(
        digest=DIGEST,
        plugin_dirs=(),
        skills=(),
        mcp_servers={},
        disallowed_tools=(),
        add_dirs=(),
        system_prompt_append="",
        notices=(),
    )
    _applier().check_flags(allowed, connectors=[], web_search=True)


# -- MCP servers from the snapshot (Task 5; R7) -------------------------------------------------


def test_the_snapshots_servers_become_typed_sdk_configs_in_document_order(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(mcp_servers=[_files("FILES_ROOT"), _docs()])
    applied = _applier(environ={"FILES_ROOT": SENTINEL}).load(path, cwd=tmp_path)
    assert list(applied.mcp_servers) == ["files", "docs"]
    assert applied.mcp_servers["files"] == {
        "type": "stdio",
        "command": LAUNCHER[0],
        "args": [*LAUNCHER[1:], "--allow", "FILES_ROOT", "--", "files-server", "--root", "."],
    }
    assert applied.mcp_servers["docs"] == {
        "type": "http",
        "url": "https://docs.example.invalid/mcp",
    }
    assert SENTINEL not in json.dumps(applied.mcp_servers)


def test_an_allowed_name_absent_from_claudeloops_environment_is_logged_by_name_only(
    tmp_path: Path,
) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(
        mcp_servers=[_files("FILES_ROOT", "FILES_HOME", "FILES_MODE"), _docs()]
    )
    logger = _RecordingLogger()
    applier = _applier(environ={"FILES_ROOT": SENTINEL, "UNRELATED": SENTINEL}, logger=logger)
    applier.load(path, cwd=tmp_path)
    assert logger.calls == [
        (
            "warning",
            "capabilities.mcp_env_absent",
            {"server": "files", "names": ["FILES_HOME", "FILES_MODE"]},
        )
    ]
    assert SENTINEL not in repr(logger.calls)


def test_nothing_is_logged_when_every_allowed_name_is_set(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(mcp_servers=[_files("FILES_ROOT"), _docs()])
    logger = _RecordingLogger()
    _applier(environ={"FILES_ROOT": SENTINEL}, logger=logger).load(path, cwd=tmp_path)
    assert logger.calls == []


def test_a_document_without_servers_gives_none(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write()
    assert _applier().load(path, cwd=tmp_path).mcp_servers == {}


# -- the worker's `vibey-web` connector (SP-LOOPS Phase 6, Task 6; R3) ---------------------------


def _vibey_web() -> McpServerSpec:
    return McpServerSpec(
        name="vibey-web",
        trust="local",
        command=("/opt/vibey/bin/vibey", "mcp", "--scope", "web", "--token-file", "/r/web-token"),
        url=None,
        env_allow=("VIBEY_HUB_URL", "VIBEY_WEB_TOKEN_FILE"),
    )


@pytest.mark.parametrize("local_backend", [False, True], ids=["anthropic", "local"])
def test_the_hub_connector_is_given_and_claude_codes_own_web_tools_stay_off(
    tmp_path: Path, local_backend: bool
) -> None:
    """The run searches the hub through `vibey-web`; Claude Code's own `WebSearch` and
    `WebFetch` are still disallowed, on either backend, and nothing else is changed by it."""
    path = CapabilityDocumentWriter(tmp_path).write(mcp_servers=[_files(), _vibey_web()])
    logger = _RecordingLogger()
    environ = {"VIBEY_HUB_URL": "http://127.0.0.1:28100", "VIBEY_WEB_TOKEN_FILE": "/r/web-token"}
    applied = _applier(local_backend=local_backend, environ=environ, logger=logger).load(
        path, cwd=tmp_path
    )
    assert list(applied.mcp_servers) == ["files", "vibey-web"]
    assert applied.mcp_servers["vibey-web"] == {
        "type": "stdio",
        "command": LAUNCHER[0],
        "args": [
            *LAUNCHER[1:],
            "--allow",
            "VIBEY_HUB_URL",
            "--allow",
            "VIBEY_WEB_TOKEN_FILE",
            "--",
            "/opt/vibey/bin/vibey",
            "mcp",
            "--scope",
            "web",
            "--token-file",
            "/r/web-token",
        ],
    }
    assert applied.disallowed_tools == CLAUDE_BUILTIN_WEB_TOOLS == ("WebSearch", "WebFetch")
    assert logger.calls == []
