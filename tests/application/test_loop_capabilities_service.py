# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One BUILD run's capability snapshot, prepared, released and swept (SP-LOOPS Phase 4, Task 8;
R1, R9, R10, R13).

The service runs over the real `[loops]` reader, the real marketplace store, resolver, document
store and pruner, all in pytest's folder, with a small stand-in for the shipped marketplace. The
person's file is `config/vibey.toml`; a project's is the worktree's `vibey.toml`, which may only
narrow.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.resolver import CapabilityResolver
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError
from vibey_runners.common.capabilities.snapshot_document_store import (
    DOCUMENT_NAME,
    SnapshotDocumentStore,
)
from vibey_runners.common.capabilities.unlocked_marketplace_error import (
    UnlockedMarketplaceError,
)

from vibey.application.dto import PreparedCapabilities, PruneReport
from vibey.application.interfaces.loop_capabilities_interface import (
    LoopCapabilitiesInterface,
    LoopMarketplacesInterface,
    LoopSnapshotRemoverInterface,
)
from vibey.application.loop_capabilities_service import LoopCapabilitiesService
from vibey.application.loops_bundle_settings import LoopsBundleSettings
from vibey.infrastructure.loops.marketplace_store import MarketplaceStore
from vibey.infrastructure.loops.snapshot_pruner import SnapshotPruner
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

SHIPPED_SOURCE = "vibey-engine 9.9.9"
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)


def _shipped(tmp_path: Path) -> Path:
    """A small stand-in for the wheel's marketplace: the research plugin and one other."""
    root = tmp_path / "wheel"
    manifest = {
        "name": "vibey",
        "plugins": [
            {"name": name, "source": f"./plugins/{name}", "description": name}
            for name in ("currency-research", "other")
        ],
    }
    files = {
        ".claude-plugin/marketplace.json": json.dumps(manifest),
        "plugins/currency-research/.claude-plugin/plugin.json": '{"name": "currency-research"}',
        "plugins/currency-research/skills/research-currency-audit-method/SKILL.md": (
            "---\nname: research-currency-audit-method\n"
            "description: Audit how current a source is.\n---\n\nBody.\n"
        ),
        "plugins/other/.claude-plugin/plugin.json": '{"name": "other"}',
    }
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    return root


class _Logger:
    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, Any]]] = []

    def bind(self, **kwargs: Any) -> _Logger:
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("debug", event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("info", event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("warning", event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append(("error", event, kwargs))


class _World:
    def __init__(
        self,
        tmp_path: Path,
        *,
        run_deadline: timedelta = 4 * HOUR,
        documents: Any = None,
        pruner: Any = None,
    ) -> None:
        self.tmp = tmp_path
        self.user_config = tmp_path / "config" / "vibey.toml"
        self.user_config.parent.mkdir(parents=True)
        self.worktree = tmp_path / "worktree"
        self.worktree.mkdir()
        shipped = _shipped(tmp_path)
        self.store = MarketplaceStore(
            self.user_config.parent / "loops", fetchers={}, shipped_root=lambda: shipped
        )
        self.logger = _Logger()
        self.service = LoopCapabilitiesService(
            settings=LoopsBundleSettings(TomlTrustedTableReader()),
            marketplaces=self.store,
            resolver=CapabilityResolver(
                self.store.lock_path, self.store.snapshots, shipped_source=SHIPPED_SOURCE
            ),
            documents=documents if documents is not None else SnapshotDocumentStore(),
            pruner=pruner if pruner is not None else SnapshotPruner(),
            user_config=self.user_config,
            run_deadline=run_deadline,
            logger=self.logger,
        )

    def person(self, text: str) -> None:
        self.user_config.write_text(text, encoding="utf-8")

    def project(self, text: str) -> Path:
        path = self.worktree / "vibey.toml"
        path.write_text(text, encoding="utf-8")
        return path

    def prepare(self, folders: tuple[Path, ...] = ()) -> PreparedCapabilities:
        return self.service.prepare(project_config=self.worktree / "vibey.toml", folders=folders)


PERSON_WITH_SERVERS = """
[[loops.mcp_servers]]
name = "files"
trust = "local"
command = ["fake-mcp", "--stdio"]
env_allow = ["FAKE_MCP_HOME"]

[[loops.mcp_servers]]
name = "tickets"
trust = "remote"
url = "https://mcp.example.test/v1"
"""


def test_the_service_and_its_seams_satisfy_their_interfaces(tmp_path: Path) -> None:
    world = _World(tmp_path)
    assert isinstance(world.service, LoopCapabilitiesInterface)
    assert isinstance(world.store, LoopMarketplacesInterface)
    assert isinstance(SnapshotPruner(), LoopSnapshotRemoverInterface)


def test_prepare_writes_one_document_in_the_run_folder_and_returns_counts(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    world.person(PERSON_WITH_SERVERS)
    inputs = tmp_path / "worktree" / ".vibey" / "inputs" / "run-1"

    prepared = world.prepare((inputs,))

    assert prepared.folder.parent == world.store.snapshots
    assert prepared.folder.name.startswith("run-")
    assert prepared.document == prepared.folder / DOCUMENT_NAME
    assert sorted(p.name for p in prepared.folder.glob("*.json")) == [DOCUMENT_NAME]
    assert (
        prepared.plugins,
        prepared.skills,
        prepared.skills_skipped,
        prepared.mcp_local,
        prepared.mcp_remote,
        prepared.notices,
    ) == (1, 1, 0, 1, 1, ())
    # The runner's own strict reading of what was written.
    document = SnapshotDocumentStore().read(prepared.document)
    assert document.digest == prepared.digest
    assert document.skills == ("currency-research:research-currency-audit-method",)
    assert document.folders == (inputs,)
    assert [server.name for server in document.mcp_servers] == ["files", "tickets"]
    assert document.builtin_web is False
    # No environment value is ever in the document: names only.
    assert "FAKE_MCP_HOME" in prepared.document.read_text(encoding="ascii")


def test_the_same_bundle_and_lock_give_the_same_digest_in_a_fresh_folder(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    first = world.prepare()
    second = world.prepare()
    assert first.digest == second.digest
    assert first.folder != second.folder


def test_a_projects_loops_table_can_only_narrow(tmp_path: Path) -> None:
    world = _World(tmp_path)
    project = world.project('[loops]\ndisable = ["currency-research"]\nbuiltin_web = true\n')

    prepared = world.service.prepare(project_config=project, folders=())

    assert (prepared.plugins, prepared.skills) == (0, 0)
    document = SnapshotDocumentStore().read(prepared.document)
    assert document.builtin_web is False  # the project's key was dropped, never applied
    assert document.plugin_dirs == ()
    [notice] = prepared.notices
    assert "builtin_web" in notice
    # Logged, never recorded: the person is told the project said it.
    assert ("warning", "loop_capabilities_project_notice", {"notice": notice}) in (
        world.logger.lines
    )


def test_an_unlocked_marketplace_is_refused_and_leaves_no_run_folder(tmp_path: Path) -> None:
    world = _World(tmp_path)
    world.person(
        '[loops]\nplugins = ["linting@acme"]\n\n'
        '[[loops.marketplaces]]\nname = "acme"\nsource = "https://git.example.test/acme.git"\n'
    )
    with pytest.raises(UnlockedMarketplaceError, match="vibey loops marketplace update acme"):
        world.prepare()
    assert list(world.store.snapshots.glob("run-*")) == []


def test_a_lock_that_cannot_be_read_is_a_resolution_error(tmp_path: Path) -> None:
    world = _World(tmp_path)
    world.store.lock_path.parent.mkdir(parents=True, exist_ok=True)
    world.store.lock_path.write_text("not a lock", encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="the loops lock cannot be read"):
        world.prepare()


class _RefusingDocuments:
    def write(self, document: Any, folder: Path) -> Path:
        raise SnapshotDocumentError(f"the capability document cannot be written at {folder}")

    def read(self, path: Path) -> Any:
        raise AssertionError("the conductor never reads its own document")


def test_a_document_that_cannot_be_written_removes_the_run_folder(tmp_path: Path) -> None:
    world = _World(tmp_path, documents=_RefusingDocuments())
    with pytest.raises(SnapshotDocumentError, match="cannot be written"):
        world.prepare()
    assert list(world.store.snapshots.glob("run-*")) == []


def test_release_removes_the_run_folder_and_nothing_else(tmp_path: Path) -> None:
    world = _World(tmp_path)
    kept = world.prepare()
    released = world.prepare()
    neighbour = world.store.snapshots / "notes.txt"
    neighbour.write_text("left alone", encoding="utf-8")

    world.service.release(released)

    assert not released.folder.exists()
    assert kept.document.is_file()
    assert neighbour.read_text(encoding="utf-8") == "left alone"
    assert world.store.snapshots.is_dir()
    assert world.logger.lines == []


def test_a_folder_release_cannot_remove_is_logged_by_name(tmp_path: Path) -> None:
    world = _World(tmp_path)
    prepared = world.prepare()
    outside = tmp_path / "run-elsewhere"
    outside.mkdir()
    stray = PreparedCapabilities(
        document=outside / DOCUMENT_NAME,
        folder=outside,
        digest=prepared.digest,
        plugins=0,
        skills=0,
        skills_skipped=0,
        mcp_local=0,
        mcp_remote=0,
        notices=(),
    )

    world.service.release(stray)

    assert outside.is_dir()  # never outside the person's snapshot folder
    assert world.logger.lines == [
        ("warning", "loop_capabilities_snapshot_kept", {"folder": str(outside)})
    ]


class _RecordingPruner:
    def __init__(self) -> None:
        self.ages: list[float] = []
        self.report = PruneReport((Path("/gone/run-1"),), ())

    def prune(self, snapshots: Path, *, older_than_seconds: float) -> PruneReport:
        self.ages.append(older_than_seconds)
        return self.report

    def remove(self, folder: Path, snapshots: Path) -> bool:
        raise AssertionError("a sweep removes by age only")


@pytest.mark.parametrize(
    ("person", "deadline", "age"),
    [
        ("", 4 * HOUR, 7 * DAY),  # the default seven days is longer than any 4-hour session
        ("[loops]\nsnapshot_max_age_days = 1\n", 4 * HOUR, DAY),
        ("[loops]\nsnapshot_max_age_days = 1\n", 30 * HOUR, 31 * HOUR),
        ("", 10 * DAY, 10 * DAY + HOUR),
    ],
)
def test_sweep_never_uses_an_age_below_the_run_deadline(
    tmp_path: Path, person: str, deadline: timedelta, age: timedelta
) -> None:
    pruner = _RecordingPruner()
    world = _World(tmp_path, run_deadline=deadline, pruner=pruner)
    world.person(person)

    report = world.service.sweep()

    assert report is pruner.report
    assert pruner.ages == [age.total_seconds()]
    assert pruner.ages[0] > deadline.total_seconds()


def test_sweep_removes_an_old_run_folder_through_the_real_pruner(tmp_path: Path) -> None:
    world = _World(tmp_path)
    prepared = world.prepare()
    report = world.service.sweep()
    assert report == PruneReport((), ())  # young: kept
    assert prepared.folder.is_dir()


def test_without_a_logger_a_notice_and_a_kept_folder_are_silent(tmp_path: Path) -> None:
    shipped = _shipped(tmp_path)
    store = MarketplaceStore(tmp_path / "loops", fetchers={}, shipped_root=lambda: shipped)
    service = LoopCapabilitiesService(
        settings=LoopsBundleSettings(TomlTrustedTableReader()),
        marketplaces=store,
        resolver=CapabilityResolver(store.lock_path, store.snapshots, shipped_source="s 1"),
        documents=SnapshotDocumentStore(),
        pruner=SnapshotPruner(),
        user_config=tmp_path / "absent.toml",
        run_deadline=HOUR,
    )
    project = tmp_path / "project.toml"
    project.write_text("[loops]\nbuiltin_web = true\n", encoding="utf-8")
    prepared = service.prepare(project_config=project, folders=())
    assert prepared.notices
    service.release(prepared)
    service.release(prepared)  # gone already: kept, and nothing said
    assert not prepared.folder.exists()
