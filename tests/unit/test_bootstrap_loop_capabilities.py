# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition of BUILD's capability snapshot in `bootstrap.py` (SP-LOOPS Phase 4, Task 8).

`loop_capabilities_service` builds the service over the person's own `[loops]`, the store beside
their `vibey.toml`, the resolver over that store's lock and snapshot folder, the document store
and the pruner, with the run deadline the sweep must outlast (R10). The function is imported by
name here, before the suite's hermetic fixture wraps the module's copy, so its own defaults are
what is tested; nothing reads the real configuration folder: it is a stand-in under pytest's
folder.
"""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

import vibey.bootstrap as bootstrap
from vibey.application.dto import PruneReport
from vibey.application.interfaces.loop_capabilities_interface import LoopCapabilitiesInterface
from vibey.application.loop_capabilities_service import LoopCapabilitiesService
from vibey.bootstrap import loop_capabilities_service


def _shipped(tmp_path: Path) -> Path:
    root = tmp_path / "wheel"
    manifest = {
        "name": "vibey",
        "plugins": [{"name": "currency-research", "source": "./plugins/currency-research"}],
    }
    files = {
        ".claude-plugin/marketplace.json": json.dumps(manifest),
        "plugins/currency-research/.claude-plugin/plugin.json": "{}",
        "plugins/currency-research/skills/audit/SKILL.md": (
            "---\nname: audit\ndescription: Audit a source.\n---\n\nBody.\n"
        ),
    }
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    return root


def test_the_service_resolves_from_the_persons_store_and_writes_its_document_there(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shipped = _shipped(tmp_path)
    monkeypatch.setattr(bootstrap, "loops_shipped_root", lambda: shipped)
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()

    service = loop_capabilities_service(timedelta(hours=2), user_config=person)

    assert isinstance(service, LoopCapabilitiesService)
    assert isinstance(service, LoopCapabilitiesInterface)
    prepared = service.prepare(project_config=None, folders=())
    snapshots = person.parent / bootstrap.LOOPS_STORE / "snapshots"
    assert prepared.folder.parent == snapshots
    assert SnapshotDocumentStore().read(prepared.document).skills == ("currency-research:audit",)
    service.release(prepared)
    assert not prepared.folder.exists()


def test_by_default_the_person_is_acp_user_config_and_the_deadline_the_engines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()
    person.write_text("[loops]\nsnapshot_max_age_days = 1\n", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "acp_user_config", lambda: person)
    monkeypatch.setenv(bootstrap.ENGINE_RUN_MINUTES_ENV, str(3 * 24 * 60))  # three days
    ages: list[float] = []

    class _Pruner:
        def prune(self, snapshots: Path, *, older_than_seconds: float) -> object:
            ages.append(older_than_seconds)
            assert snapshots == person.parent / bootstrap.LOOPS_STORE / "snapshots"
            return PruneReport((), ())

        def remove(self, folder: Path, snapshots: Path) -> bool:
            raise AssertionError("not here")

    monkeypatch.setattr(bootstrap, "loops_snapshot_pruner", _Pruner)

    loop_capabilities_service().sweep()

    # The person's one day is shorter than a three-day session: the deadline and an hour win.
    assert ages == [(timedelta(days=3) + timedelta(hours=1)).total_seconds()]


def test_the_suite_never_reaches_the_developers_own_loops(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The hermetic fixture in `tests/conftest.py` wraps the module's copy: what the worker
    composes in a test resolves from a person in pytest's own folder."""
    assert bootstrap.loop_capabilities_service is not loop_capabilities_service
    service = bootstrap.loop_capabilities_service(timedelta(hours=1))
    person = service._user_config  # noqa: SLF001
    assert person.is_relative_to(tmp_path_factory.getbasetemp())
    assert person != bootstrap.acp_user_config()
