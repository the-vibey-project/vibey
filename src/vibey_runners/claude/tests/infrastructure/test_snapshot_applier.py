# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""infrastructure/capabilities/snapshot_applier.py — a run's capability document, read strictly
and turned into what one claudeloop session is given (SP-LOOPS Phase 4, Task 4; R4, R9, R11,
R12; Review Focus 5)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

from claudeloop.domain.capabilities import CLAUDE_BUILTIN_WEB_TOOLS, AppliedCapabilities
from claudeloop.domain.errors import CapabilityFlagConflict, CapabilitySnapshotRefused
from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
from claudeloop.infrastructure.interfaces import CapabilitySnapshotApplierInterface
from tests.capability_documents import DIGEST, CapabilityDocumentWriter

SENTINEL = "SENTINEL-VALUE-7731"


def _applier(*, local_backend: bool = False) -> CapabilitySnapshotApplier:
    return CapabilitySnapshotApplier(SnapshotDocumentStore(), local_backend=local_backend)


def test_the_applier_satisfies_its_interface() -> None:
    assert isinstance(_applier(), CapabilitySnapshotApplierInterface)


def test_builtin_web_false_disallows_websearch_and_webfetch(tmp_path: Path) -> None:
    writer = CapabilityDocumentWriter(tmp_path)
    inputs = Path("/inputs/one")
    path = writer.write(builtin_web=False, folders=[inputs])
    applied = _applier().load(path)
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
    applied = _applier().load(path)
    assert applied.disallowed_tools == ()
    assert applied.notices == ()


def test_a_local_backend_disallows_them_even_when_builtin_web_is_true_and_says_so(
    tmp_path: Path,
) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(builtin_web=True)
    applied = _applier(local_backend=True).load(path)
    assert applied.disallowed_tools == CLAUDE_BUILTIN_WEB_TOOLS
    assert len(applied.notices) == 1
    assert "builtin_web" in applied.notices[0]
    assert "local backend" in applied.notices[0]


def test_a_local_backend_with_builtin_web_false_has_nothing_to_say(tmp_path: Path) -> None:
    path = CapabilityDocumentWriter(tmp_path).write(builtin_web=False)
    applied = _applier(local_backend=True).load(path)
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
        _applier().load(path)
    message = str(caught.value)
    assert str(path) in message
    assert SENTINEL not in message
    assert SENTINEL not in caught.value.reason


def test_a_missing_document_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "gone" / "capabilities.json"
    with pytest.raises(CapabilitySnapshotRefused, match="refused"):
        _applier().load(path)


class _UnreadableStore:
    def write(self, document: SnapshotDocumentInterface, folder: Path) -> Path:
        raise AssertionError("never written here")

    def read(self, path: Path) -> SnapshotDocumentInterface:
        raise OSError(f"cannot read {SENTINEL}")


def test_an_os_error_while_reading_is_refused_without_its_text(tmp_path: Path) -> None:
    path = tmp_path / "capabilities.json"
    applier = CapabilitySnapshotApplier(_UnreadableStore(), local_backend=False)
    with pytest.raises(CapabilitySnapshotRefused) as caught:
        applier.load(path)
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
