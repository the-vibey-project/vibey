# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A crashed worker's session token goes with its run folder (SP-LOOPS Phase 6, Task 7; R1, R4).

A BUILD run's token file is written into the run's own snapshot folder, the one the capability
service prepared and the Phase 4 snapshot sweep removes (`LoopCapabilitiesService.sweep`, age =
the longer of `[loops] snapshot_max_age_days` and the run deadline plus `DEADLINE_MARGIN`). A
worker that dies never revokes the grant nor releases the folder; the next worker's sweeps remove
both: the folder (and the token file in it) once it is old enough, and the registry entry once it
has expired. No token file lives anywhere else, so none can outlive its folder, and the folder
outlives the token's own validity, so by the time the file is removed the hub refuses it anyway.

Composed as the worker composes them (`bootstrap.loop_capabilities_service`,
`bootstrap.run_web_grants`), over real files in pytest's folder; only where the hub runs is a
stand-in, as no hub runs here.
"""

from __future__ import annotations

import json
import os
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

import vibey.bootstrap as bootstrap
from vibey.application.loop_capabilities_service import DEADLINE_MARGIN, LoopCapabilitiesService
from vibey.application.run_web_grants import RunWebGrants
from vibey.application.session_registry_sweep import SessionRegistrySweep
from vibey.bootstrap import loop_capabilities_service, run_web_grants
from vibey.infrastructure.hub.session_registry import SessionRegistry
from vibey.infrastructure.hub.session_token_store import WEB_TOKEN_FILE

pytestmark = pytest.mark.skipif(os.name != "posix", reason="file modes are POSIX")

DEADLINE = timedelta(hours=30)
"""Longer than the person's one day, so the run deadline and the margin decide the folder's age."""
LIFETIME = (DEADLINE + DEADLINE_MARGIN).total_seconds()
HUB = "http://127.0.0.1:8765"


def _shipped(tmp_path: Path) -> Path:
    """The marketplace the person's default bundle names, as `test_bootstrap_loop_capabilities`
    ships it: one plugin with one skill."""
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


class _Hub:
    """A hub is running: the worker mints each run its grant."""

    def __init__(self, state_dir: Path, **_: object) -> None:
        self.state_dir = state_dir

    def url(self) -> str:
        return HUB


def _age(folder: Path, seconds: float) -> None:
    """Every change at the top of `folder` happened `seconds` ago (the sweep's rule)."""
    then = time.time() - seconds
    for entry in os.scandir(folder):
        os.utime(entry.path, (then, then), follow_symlinks=False)
    os.utime(folder, (then, then))


Worker = tuple[LoopCapabilitiesService, RunWebGrants, Path, Path]


@pytest.fixture
def worker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Worker:
    monkeypatch.setattr(bootstrap, "loops_shipped_root", lambda: _shipped(tmp_path))
    monkeypatch.setattr(bootstrap, "RunningHub", _Hub)
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()
    person.write_text("[loops]\nsnapshot_max_age_days = 1\n", encoding="utf-8")
    state = tmp_path / "hub-state"
    capabilities = loop_capabilities_service(DEADLINE, user_config=person)
    grants = run_web_grants(DEADLINE, state_dir=state)
    snapshots = person.parent / bootstrap.LOOPS_STORE / "snapshots"
    return capabilities, grants, snapshots, state


def test_the_token_file_lives_in_the_very_folder_the_snapshot_sweep_removes(
    worker: Worker,
) -> None:
    capabilities, grants, snapshots, _ = worker
    prepared = capabilities.prepare(project_config=None, folders=())

    web = grants.open(uuid4(), prepared.folder)

    assert web.state == "hub"
    assert web.token_file == prepared.folder / WEB_TOKEN_FILE
    # The pruner removes `run-*` folders directly in the person's snapshot folder: this one.
    assert prepared.folder.parent == snapshots
    assert prepared.folder.name.startswith("run-")
    grants.close(web)
    capabilities.release(prepared)


def test_a_crashed_runs_token_goes_with_its_folder_and_its_entry_once_expired(
    worker: Worker,
) -> None:
    """The worker died mid-run: no revocation, no release. Past the run deadline and the margin,
    the next worker's two sweeps leave nothing of it, and running them again changes nothing."""
    capabilities, grants, snapshots, state = worker
    crashed = capabilities.prepare(project_config=None, folders=())
    web = grants.open(uuid4(), crashed.folder)
    token_file, grant = web.token_file, web.grant
    assert token_file is not None and grant is not None and token_file.exists()
    _age(crashed.folder, LIFETIME + 60)
    registry = SessionRegistry(state)
    sessions = SessionRegistrySweep(registry, clock=lambda: grant.expires_at)

    swept = capabilities.sweep()
    expired = sessions.sweep()

    assert swept.removed == (crashed.folder,)
    assert not token_file.exists() and not crashed.folder.exists()
    assert expired.removed == (grant.name,)
    assert registry.entries().entries == ()
    # Idempotent under replay.
    assert capabilities.sweep().removed == ()
    assert sessions.sweep().removed == ()


def test_a_run_inside_its_deadline_keeps_its_folder_its_token_and_its_entry(
    worker: Worker,
) -> None:
    """A live run on another worker, a minute short of its deadline: neither sweep touches it,
    run once or twice."""
    capabilities, grants, _, state = worker
    live = capabilities.prepare(project_config=None, folders=())
    web = grants.open(uuid4(), live.folder)
    token_file = web.token_file
    assert token_file is not None
    _age(live.folder, DEADLINE.total_seconds() - 60)
    sessions = SessionRegistrySweep(SessionRegistry(state))

    for _ in range(2):
        assert capabilities.sweep().removed == ()
        assert sessions.sweep().removed == ()

    assert token_file.exists()
    assert web.grant is not None
    assert SessionRegistry(state).find(web.grant.digest) == web.grant.principal
    grants.close(web)
    capabilities.release(live)


def test_the_folder_outlives_the_token_so_the_file_is_never_removed_while_it_still_works(
    worker: Worker,
) -> None:
    """The token is honoured until the run deadline plus `DEADLINE_MARGIN` after its mint; the
    folder is kept at least that long after its last change, and the mint is a change in it."""
    capabilities, grants, _, _ = worker
    prepared = capabilities.prepare(project_config=None, folders=())
    before = time.time()
    web = grants.open(uuid4(), prepared.folder)
    grant = web.grant
    assert grant is not None
    assert before + LIFETIME <= grant.expires_at <= time.time() + LIFETIME
    # A minute short of the token's lifetime since the mint: the folder and the file stay.
    _age(prepared.folder, LIFETIME - 60)
    assert capabilities.sweep().removed == ()
    assert web.token_file is not None and web.token_file.exists()
    # Past it, they go: the token was refused by then.
    _age(prepared.folder, LIFETIME + 60)
    assert capabilities.sweep().removed == (prepared.folder,)
    assert not web.token_file.exists()
    grants.close(web)  # the worker that minted it may still revoke: idempotent, file or not
    assert SessionRegistry(worker[3]).entries().entries == ()
