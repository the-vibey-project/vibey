# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""BUILD gives each engine run its own web access and takes it back however the run ends
(SP-LOOPS Phase 6, Task 5; R1, R4; Review Focus 4).

The capability service, the ledger, the engine and the web grants all write into one ordered
log, so "revoked before the run's folder is released, on every exit" is asserted, not assumed.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository, handle_leased, make_job
from tests.application.test_build_implement_capabilities import (
    SNAPSHOTTED,
    _Capabilities,
    _Engine,
    _Ledger,
)
from tests.application.test_build_implement_handler import (
    FakeProvisioner,
    FakeWorktrees,
    FixedClock,
    _RecordingWindDown,
    _wind_down_script,
)
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.dto import RunHandle, RunSpec, RunWebAccess, SessionGrant
from vibey.application.run_web_grants import RunWebGrants
from vibey.application.worker import Failure, Success
from vibey.domain.engine import EngineDescriptor
from vibey.domain.session_principal import SessionPrincipal
from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER
from vibey.infrastructure.engines.descriptors import CLAUDELOOP, CODEXLOOP, QWENLOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine

HUB = "http://127.0.0.1:28100"


def _grant(run_id: UUID, folder: Path) -> SessionGrant:
    return SessionGrant(
        token_file=folder / "web-token",
        principal=SessionPrincipal(name=f"session:{run_id}", run_id=run_id, expires_at=9e9),
        digest="f" * 64,
    )


class _Web:
    """Opens with a grant when there is a hub and a folder, and logs open and close."""

    def __init__(self, log: list[str], *, hub: bool = True, error: Exception | None = None):
        self.log = log
        self.hub = hub
        self.error = error
        self.opened: list[tuple[UUID, Path | None]] = []
        self.closed: list[RunWebAccess] = []

    def open(self, run_id: UUID, folder: Path | None) -> RunWebAccess:
        self.log.append("open")
        self.opened.append((run_id, folder))
        if self.error is not None:
            raise self.error
        if folder is None:
            return RunWebAccess("none", reason=NO_RUN_FOLDER)
        if not self.hub:
            return RunWebAccess("none", reason=NO_HUB)
        return RunWebAccess("hub", hub_url=HUB, grant=_grant(run_id, folder))

    def close(self, access: RunWebAccess) -> None:
        self.log.append("close")
        self.closed.append(access)


class _Harness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        descriptor: EngineDescriptor = CLAUDELOOP,
        engine: ScriptedEngine | None = None,
        web: Any = None,
        capabilities: bool = True,
        wind_down: Any = None,
        hub: bool = True,
    ) -> None:
        self.tmp = tmp_path
        self.log: list[str] = []
        self.capabilities = _Capabilities(tmp_path / "snapshots", self.log)
        self.ledger = _Ledger(self.log)
        if engine is None:
            engine = _Engine(descriptor=descriptor, base_dir=tmp_path / "engine")
        engine.log = self.log  # type: ignore[attr-defined]
        self.engine = engine
        self.web = _Web(self.log, hub=hub) if web is None else web
        self.handler = BuildImplementHandler(
            worktrees=FakeWorktrees(tmp_path / "worktrees"),
            provisioner=FakeProvisioner(),
            engine=engine,
            ledger=self.ledger,
            jobs=FakeJobRepository(),
            clock=FixedClock(),
            wind_down=wind_down,
            capabilities=self.capabilities if capabilities else None,
            web=self.web,
        )

    async def run(self) -> Any:
        job = replace(
            make_job(uuid4()),
            kind="build.implement",
            work_item_id="item-1",
            attempts=1,
            payload={"title": "do the thing"},
        )
        return await handle_leased(self.handler, job)


async def test_with_a_hub_the_run_holds_its_own_grant_in_its_own_folder(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)

    assert isinstance(await harness.run(), Success)

    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    [prepared] = harness.capabilities.prepared
    assert harness.web.opened == [(spec.run_id, prepared.folder)]
    assert spec.web is not None and spec.web.state == "hub"
    assert spec.web.token_file == prepared.folder / "web-token"
    assert harness.web.closed == [spec.web]
    assert harness.log[:4] == ["prepare", "open", f"record:{SNAPSHOTTED}", "start"]
    assert harness.log[-2:] == ["close", "release"]


async def test_without_a_hub_the_run_is_told_none_and_why(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, hub=False)

    assert isinstance(await harness.run(), Success)

    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert spec.web == RunWebAccess("none", reason=NO_HUB)
    assert harness.log[-2:] == ["close", "release"]


async def test_the_local_runner_is_given_its_grant_too(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, descriptor=QWENLOOP)
    assert isinstance(await harness.run(), Success)
    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert spec.web is not None and spec.web.state == "hub"


async def test_an_engine_with_no_run_folder_of_its_own_has_no_web(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, descriptor=CODEXLOOP)

    assert isinstance(await harness.run(), Success)

    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert harness.web.opened == [(spec.run_id, None)]
    assert spec.web == RunWebAccess("none", reason=NO_RUN_FOLDER)
    assert harness.log[-1] == "close"


async def test_without_a_capability_service_the_run_has_no_folder_and_no_web(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path, capabilities=False)
    assert isinstance(await harness.run(), Success)
    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert spec.web == RunWebAccess("none", reason=NO_RUN_FOLDER)


async def test_without_a_web_service_the_run_spec_says_nothing(tmp_path: Path) -> None:
    engine = _Engine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    engine.log = []
    handler = BuildImplementHandler(
        worktrees=FakeWorktrees(tmp_path / "worktrees"),
        provisioner=FakeProvisioner(),
        engine=engine,
        ledger=_Ledger([]),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )
    job = replace(make_job(uuid4()), kind="build.implement", work_item_id="item-1", attempts=1)
    assert isinstance(await handle_leased(handler, job), Success)
    assert engine.specs[0].web is None


async def test_the_grant_is_revoked_before_release_on_failure_and_wind_down(
    tmp_path: Path,
) -> None:
    failing = _Harness(
        tmp_path / "failure",
        engine=_Engine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "failure-engine",
            script=_wind_down_script(),
            exit_code_script=[1],
        ),
    )
    assert isinstance(await failing.run(), Failure)
    winding = _Harness(
        tmp_path / "wind-down",
        engine=_Engine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "wind-down-engine",
            script=_wind_down_script(),
            exit_code_script=[75],
        ),
        wind_down=_RecordingWindDown(),
    )
    assert await winding.run() == Success({"wind_down": True})

    for harness in (failing, winding):
        assert len(harness.web.closed) == 1
        assert harness.log[-2:] == ["close", "release"]


class _Raising(_Engine):
    error: BaseException

    async def start(self, spec: RunSpec) -> RunHandle:
        self.log.append("start")
        raise self.error


@pytest.mark.parametrize(
    "error",
    [RuntimeError("the runner could not be spawned"), asyncio.CancelledError()],
    ids=["exception", "cancellation"],
)
async def test_the_grant_is_revoked_before_release_when_the_run_raises_or_is_cancelled(
    tmp_path: Path, error: BaseException
) -> None:
    engine = _Raising(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    engine.error = error
    harness = _Harness(tmp_path, engine=engine)

    with pytest.raises(type(error)):
        await harness.run()

    assert harness.log == [
        "prepare",
        "open",
        f"record:{SNAPSHOTTED}",
        "start",
        "close",
        "release",
    ]


async def test_an_open_that_raises_still_releases_the_folder(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)
    harness.web = _Web(harness.log, error=RuntimeError("a bug"))
    harness.handler._web = harness.web  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="a bug"):
        await harness.run()

    assert harness.log == ["prepare", "open", "release"]
    assert harness.web.closed == []


class _Hub:
    def url(self) -> str | None:
        return HUB


class _StuckPrincipals:
    """Mints a grant into the folder, and cannot revoke it."""

    def mint(self, run_id: UUID, folder: Path, now: float) -> SessionGrant:
        return _grant(run_id, folder)

    def revoke(self, grant: SessionGrant) -> None:
        raise OSError("the registry folder cannot be written")

    def lookup(self, token: str, now: float) -> SessionPrincipal | None:
        return None


async def test_a_revocation_that_fails_never_replaces_the_runs_outcome(tmp_path: Path) -> None:
    web = RunWebGrants(hub=_Hub(), principals=_StuckPrincipals(), clock=lambda: 1.0)
    success = _Harness(tmp_path / "success", web=web)
    assert isinstance(await success.run(), Success)

    failing = _Harness(
        tmp_path / "failure",
        web=web,
        engine=_Engine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "failure-engine",
            script=_wind_down_script(),
            exit_code_script=[1],
        ),
    )
    assert isinstance(await failing.run(), Failure)
    for harness in (success, failing):
        assert harness.log[-1] == "release"
