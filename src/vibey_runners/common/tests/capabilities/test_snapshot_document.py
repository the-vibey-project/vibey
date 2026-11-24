# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The run's capability document: what a loop is given, as the conductor writes it and a runner
reads it back, refusing anything it would not have written (SP-LOOPS Phase 4, Task 2; R1, R6,
R13; Review Focus 5)."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from fakes import unsearchable

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.interfaces.snapshot_document_interface import (
    SnapshotDocumentInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.snapshot_document import (
    DOCUMENT_VERSION,
    SnapshotDocument,
)
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError

DIGEST = "sha256:" + "ab" * 32
FILES = McpServerSpec("files", "local", ("fake-mcp", "--stdio"), None, ("HOME", "FAKE_MCP_VAR"))
TICKETS = McpServerSpec("tickets", "remote", None, "https://mcp.example.test/v1", ())


def _plugin(folder: Path, *parts: str) -> Path:
    """A plugin folder under `folder`, holding the marker a copied plugin carries."""
    plugin = folder.joinpath(*parts)
    (plugin / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text('{"name": "p"}', encoding="utf-8")
    return plugin


@pytest.fixture
def run(tmp_path: Path) -> Path:
    folder = Path(os.path.realpath(tmp_path)) / "snapshots" / "run-abc"
    folder.mkdir(mode=0o700, parents=True)
    return folder


def _snapshot(run: Path) -> CapabilitySnapshot:
    research = _plugin(run, "vibey", "plugins", "currency-research")
    linting = _plugin(run, "acme", "plugins", "linting")
    skills = SkillCatalog(
        (
            SkillEntry("currency-research", "research-currency-audit-method", "Audits.", research),
            SkillEntry("linting", "lint", "Lints.", linting),
        ),
        ((linting / "skills" / "gone", "a symlink, which a snapshot never copies"),),
    )
    return CapabilitySnapshot((research, linting), skills, (FILES, TICKETS), DIGEST, run)


def _document(run: Path, **bundle: object) -> SnapshotDocument:
    raw: dict[str, object] = {"plugins": [], **bundle}
    return SnapshotDocument.of(_snapshot(run), BundleSpec.from_mapping(raw), [run.parent / "in"])


def _raw(run: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(_document(run).to_json())
    return loaded


def _refused(run: Path, change: Callable[[dict[str, Any]], object]) -> SnapshotDocumentError:
    raw = _raw(run)
    change(raw)
    with pytest.raises(SnapshotDocumentError) as caught:
        SnapshotDocument.from_json(json.dumps(raw), run)
    return caught.value


def test_a_document_round_trips_through_json(run: Path) -> None:
    document = _document(
        run, builtin_web=True, instruction_files=["CLAUDE.md"], instruction_max_bytes=512
    )
    assert isinstance(document, SnapshotDocumentInterface)
    assert document.version == DOCUMENT_VERSION == 2
    assert document.digest == DIGEST
    assert document.skills == ("currency-research:research-currency-audit-method", "linting:lint")
    assert document.mcp_servers == (FILES, TICKETS)
    assert (document.builtin_web, document.instruction_files) == (True, ("CLAUDE.md",))
    assert document.instruction_max_bytes == 512
    assert document.folders == (run.parent / "in",)
    assert SnapshotDocument.from_json(document.to_json(), run) == document


def test_a_document_round_trips_both_budgets(run: Path) -> None:
    document = _document(run, capability_prompt_tokens=4096, capability_answer_tokens=256)
    assert (document.capability_prompt_tokens, document.capability_answer_tokens) == (4096, 256)
    raw = json.loads(document.to_json())
    assert (raw["capability_prompt_tokens"], raw["capability_answer_tokens"]) == (4096, 256)
    assert SnapshotDocument.from_json(document.to_json(), run) == document
    default = _document(run)
    assert (default.capability_prompt_tokens, default.capability_answer_tokens) == (3072, 3000)


def test_a_version_1_document_is_refused(run: Path) -> None:
    """A version-1 document carries neither budget; it is refused by its version, before a
    missing key is looked for, and the refusal names the version this runner knows."""

    def version_1(raw: dict[str, Any]) -> None:
        raw["version"] = 1
        del raw["capability_prompt_tokens"], raw["capability_answer_tokens"]

    error = _refused(run, version_1)
    assert "version 1 is not one this runner knows (it knows 2)" in str(error)


def test_the_json_is_canonical_ascii_with_sorted_keys(run: Path) -> None:
    text = _document(run).to_json()
    assert text.isascii()
    assert list(json.loads(text)) == sorted(json.loads(text))
    assert (
        SnapshotDocument.from_json(text, run).to_json() == text
    )  # the same document, the same text


def test_the_servers_are_written_in_the_loops_table_shape(run: Path) -> None:
    servers = _raw(run)["mcp_servers"]
    assert servers == [
        {
            "name": "files",
            "trust": "local",
            "command": ["fake-mcp", "--stdio"],
            "env_allow": ["HOME", "FAKE_MCP_VAR"],
        },
        {
            "name": "tickets",
            "trust": "remote",
            "url": "https://mcp.example.test/v1",
            "env_allow": [],
        },
    ]
    assert BundleSpec.from_mapping({"mcp_servers": servers}).mcp_servers == (FILES, TICKETS)


def test_the_json_holds_no_env_value_only_env_allow_names(
    run: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FAKE_MCP_VAR", "fake-value-sentinel-7c1d")
    text = _document(run).to_json()
    assert "FAKE_MCP_VAR" in text
    assert "fake-value-sentinel-7c1d" not in text
    assert os.environ["HOME"] not in text


def test_a_plugin_folder_outside_the_documents_folder_is_refused(run: Path) -> None:
    outside = _plugin(run.parent, "elsewhere", "p")
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(outside)))
    assert "plugin_dirs[2]" in str(error) and "outside" in str(error)
    inside_link = run / "vibey" / "plugins" / "link"
    inside_link.symlink_to(outside, target_is_directory=True)
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(inside_link)))
    assert "plugin_dirs[2]" in str(error) and "outside" in str(error)
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(run)))
    assert "outside" in str(error)


@pytest.mark.parametrize(
    "entry",
    ["vibey/plugins/currency-research", "{run}/vibey/plugins/../plugins/currency-research", 7],
)
def test_a_plugin_folder_must_be_absolute_and_plain(run: Path, entry: object) -> None:
    value = entry.format(run=run) if isinstance(entry, str) else entry
    error = _refused(run, lambda raw: raw["plugin_dirs"].__setitem__(0, value))
    assert "plugin_dirs[0]" in str(error)


def test_a_plugin_folder_must_hold_its_plugin_json(run: Path) -> None:
    bare = run / "vibey" / "plugins" / "bare"
    bare.mkdir(parents=True)
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(bare)))
    assert ".claude-plugin/plugin.json" in str(error)
    linked = run / "vibey" / "plugins" / "linked"
    (linked / ".claude-plugin").mkdir(parents=True)
    (linked / ".claude-plugin" / "plugin.json").symlink_to(
        run / "vibey" / "plugins" / "currency-research" / ".claude-plugin" / "plugin.json"
    )
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(linked)))
    assert ".claude-plugin/plugin.json" in str(error)
    afile = run / "vibey" / "plugins" / "afile"
    afile.write_text("not a folder", encoding="utf-8")
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(afile)))
    assert ".claude-plugin/plugin.json" in str(error)


def test_a_plugin_folder_that_cannot_be_checked_is_refused(run: Path) -> None:
    hidden = _plugin(run, "vibey", "plugins", "hidden")
    with unsearchable(hidden / ".claude-plugin"):
        error = _refused(run, lambda raw: raw["plugin_dirs"].append(str(hidden)))
    assert "plugin_dirs[2] cannot be checked" in str(error)
    error = _refused(run, lambda raw: raw["plugin_dirs"].append(f"{run}/vibey/a\x00b"))
    assert "plugin_dirs[2] cannot be checked" in str(error)


@pytest.mark.parametrize("version", [0, 1, 3, True, "2", None])
def test_an_unknown_version_is_refused(run: Path, version: object) -> None:
    error = _refused(run, lambda raw: raw.__setitem__("version", version))
    assert "version" in str(error)


@pytest.mark.parametrize(
    "digest", ["sha256:" + "AB" * 32, "sha256:" + "a" * 63, "md5:" + "a" * 64, "", 3]
)
def test_a_digest_that_is_not_a_sha256_is_refused(run: Path, digest: object) -> None:
    error = _refused(run, lambda raw: raw.__setitem__("digest", digest))
    assert "digest" in str(error)


@pytest.mark.parametrize("folder", ["relative/in", "", 3])
def test_a_folder_that_is_not_absolute_is_refused(run: Path, folder: object) -> None:
    error = _refused(run, lambda raw: raw["folders"].append(folder))
    assert "folders[1]" in str(error)


@pytest.mark.parametrize("folder", [Path("relative/in"), Path("a\x00b").absolute()])
def test_a_folder_that_is_not_absolute_is_refused_when_the_document_is_made(
    run: Path, folder: Path
) -> None:
    """The writer refuses what the reader would, so a document a runner would refuse is never
    written: the same error type, the same message."""
    with pytest.raises(SnapshotDocumentError, match=r"folders\[1\] must be an absolute path"):
        SnapshotDocument.of(_snapshot(run), BundleSpec.default(), [run.parent / "in", folder])


@pytest.mark.parametrize(
    "skill", ["lint", "linting:", ":lint", "linting:lint:x", "linting:../x", "-p:s", 4]
)
def test_a_skill_that_is_not_plugin_colon_skill_is_refused(run: Path, skill: object) -> None:
    error = _refused(run, lambda raw: raw["skills"].append(skill))
    assert "skills[2]" in str(error)


@pytest.mark.parametrize("name", ["VIBEY_HUB_TOKEN", "MY_API_KEY"])
def test_a_secret_named_env_allow_in_a_document_is_refused(run: Path, name: str) -> None:
    error = _refused(run, lambda raw: raw["mcp_servers"][0]["env_allow"].append(name))
    assert "loops.mcp_servers[0].env_allow[2]" in str(error)
    assert "secret" in str(error)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("builtin_web", "yes"),
        ("instruction_files", ["a/CLAUDE.md"]),
        ("instruction_max_bytes", 0),
        ("capability_prompt_tokens", 4097),
        ("capability_answer_tokens", 255),
        ("mcp_servers", [{"name": "x", "trust": "remote", "url": "http://insecure.test/"}]),
    ],
)
def test_the_bundle_rule_governs_the_document_too(run: Path, key: str, value: object) -> None:
    error = _refused(run, lambda raw: raw.__setitem__(key, value))
    assert f"loops.{key}" in str(error)


@pytest.mark.parametrize(
    "key",
    [
        "version",
        "digest",
        "plugin_dirs",
        "folders",
        "skills",
        "capability_prompt_tokens",
        "capability_answer_tokens",
    ],
)
def test_a_missing_key_is_refused(run: Path, key: str) -> None:
    assert key in str(_refused(run, lambda raw: raw.pop(key)))


def test_an_unknown_key_is_refused(run: Path) -> None:
    assert "settings" in str(_refused(run, lambda raw: raw.__setitem__("settings", {})))


@pytest.mark.parametrize("key", ["plugin_dirs", "folders", "skills"])
def test_each_list_must_be_a_list(run: Path, key: str) -> None:
    assert key in str(_refused(run, lambda raw: raw.__setitem__(key, "not-a-list")))


@pytest.mark.parametrize("text", ["", "{", "[]", '"text"', "[" * 100_000 + "]" * 100_000])
def test_text_that_is_not_a_json_object_is_refused(run: Path, text: str) -> None:
    with pytest.raises(SnapshotDocumentError, match="capability document"):
        SnapshotDocument.from_json(text, run)
