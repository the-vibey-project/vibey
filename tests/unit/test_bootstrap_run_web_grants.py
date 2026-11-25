# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The composition of each BUILD run's web access in `bootstrap.py` (SP-LOOPS Phase 6, Task 5).

`run_web_grants` finds the running hub in the hub's state folder and mints into that folder's
session registry. The function is imported by name, before the suite's hermetic fixture wraps the
module's copy, so its own defaults are tested; the hub's lock holder is the only seam replaced,
and nothing reads the real configuration or state folder.
"""

from __future__ import annotations

import os
import stat
import time
from datetime import timedelta
from pathlib import Path
from uuid import UUID

import pytest

import vibey.bootstrap as bootstrap
from vibey.application.interfaces import RunWebGrantsInterface
from vibey.application.loop_capabilities_service import DEADLINE_MARGIN
from vibey.application.run_web_grants import RunWebGrants
from vibey.bootstrap import run_web_grants
from vibey.domain.session_web_state import NO_HUB
from vibey.infrastructure.hub import running_hub
from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord

RUN = UUID("00000000-0000-4000-8000-000000000009")


def _run_folder(tmp_path: Path) -> Path:
    folder = tmp_path / "run"
    folder.mkdir(mode=0o700)
    return folder


def test_without_a_hub_a_run_is_told_none(tmp_path: Path) -> None:
    grants = run_web_grants(timedelta(hours=2), state_dir=tmp_path / "state")
    assert isinstance(grants, RunWebGrants)
    assert isinstance(grants, RunWebGrantsInterface)
    access = grants.open(RUN, _run_folder(tmp_path))
    assert (access.state, access.reason) == ("none", NO_HUB)
    assert not (tmp_path / "state" / "sessions").exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX file modes")
def test_with_a_hub_a_run_is_minted_into_the_hubs_own_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = tmp_path / "state"
    LocalTokenStore(state).record_serving(
        ServingRecord(host="127.0.0.1", port=28100, pid=os.getpid())
    )

    class _Held:
        def __init__(self, state_dir: Path) -> None:
            assert state_dir == state

        def held_by(self) -> int:
            return os.getpid()

    monkeypatch.setattr(running_hub, "ServeLock", _Held)
    grants = run_web_grants(timedelta(hours=2), state_dir=state)
    folder = _run_folder(tmp_path)

    lifetime = (timedelta(hours=2) + DEADLINE_MARGIN).total_seconds()
    before = time.time()
    access = grants.open(RUN, folder)
    after = time.time()

    assert access.state == "hub" and access.hub_url == "http://127.0.0.1:28100"
    assert access.grant is not None
    assert stat.S_IMODE(os.stat(folder / "web-token").st_mode) == 0o600
    assert [entry.suffix for entry in (state / "sessions").iterdir()] == [".json"]
    # R4, minted with the wall clock the hub reads expiry against.
    assert before + lifetime <= access.grant.expires_at <= after + lifetime
    grants.close(access)
    assert not (folder / "web-token").exists()
    assert list((state / "sessions").iterdir()) == []


def test_by_default_the_state_folder_is_the_persons_own_hub_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    person = tmp_path / "config" / "vibey.toml"
    person.parent.mkdir()
    state = tmp_path / "persons-hub"
    person.write_text(f'[hub]\nstate_dir = "{state}"\n', encoding="utf-8")
    monkeypatch.setattr(bootstrap, "acp_user_config", lambda: person)
    seen: list[Path] = []

    class _Hub:
        def __init__(self, state_dir: Path, **_: object) -> None:
            seen.append(state_dir)

        def url(self) -> None:
            return None

    monkeypatch.setattr(bootstrap, "RunningHub", _Hub)
    run_web_grants(timedelta(hours=2)).open(RUN, _run_folder(tmp_path))
    assert seen == [state]
