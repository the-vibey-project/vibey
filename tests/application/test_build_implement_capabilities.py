# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""BUILD gives a loop that takes the snapshot its locked capabilities, and the ledger records
them before the engine starts (SP-LOOPS Phase 4, Task 8; R2, R3, R9, R10; Review Focus 4).

The handler runs with a recording capability service, a scripted engine that keeps every spec it
was started with (and the argv `build_argv` makes of it), and a ledger that writes into the same
ordered log as the service and the engine, so the order is asserted, not assumed.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from vibey_runners.common.capabilities.lock_mismatch_error import LockMismatchError
from vibey_runners.common.capabilities.snapshot_document_error import SnapshotDocumentError
from vibey_runners.common.capabilities.unlocked_marketplace_error import (
    UnlockedMarketplaceError,
)

from tests.application.fakes import FakeJobRepository, handle_leased, make_job
from tests.application.test_build_implement_handler import (
    FakeProvisioner,
    FakeWorktrees,
    FixedClock,
    _RecordingWindDown,
    _wind_down_script,
)
from tests.application.test_build_implement_inputs import _World as _InputsWorld
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.dto import (
    EngineEvent,
    PreparedCapabilities,
    PruneReport,
    RunHandle,
    RunSpec,
)
from vibey.application.interfaces.run_inputs_interface import RunInputsInterface
from vibey.application.worker import Failure, Park, Success
from vibey.domain.config import ConfigError
from vibey.domain.engine import EngineDescriptor
from vibey.domain.job import LOOP_CAPABILITIES_GATE_KIND, FailureClass
from vibey.domain.ledger import EventKind
from vibey.domain.loop_capabilities import LOOP_CAPABILITIES_RECORD
from vibey.infrastructure.engines.argv import build_argv
from vibey.infrastructure.engines.descriptors import (
    CLAUDELOOP,
    CLAUDELOOP_LOCAL,
    CODEXLOOP,
    GPTOSSLOOP,
)
from vibey.infrastructure.engines.scripted import ScriptedEngine

DIGEST = "sha256:" + "a" * 64
SNAPSHOTTED = EventKind.LOOP_CAPABILITIES_SNAPSHOTTED.value
SEED = "Objective: resume without losing [q-77]."


class _Capabilities:
    """Prepares a folder with a document in it, the way the real service does, and writes each
    call into the shared log."""

    def __init__(self, root: Path, log: list[str], error: BaseException | None = None) -> None:
        self.root = root
        self.log = log
        self.error = error
        self.calls: list[tuple[Path | None, tuple[Path, ...]]] = []
        self.prepared: list[PreparedCapabilities] = []
        self.released: list[PreparedCapabilities] = []

    def prepare(
        self, *, project_config: Path | None, folders: Sequence[Path]
    ) -> PreparedCapabilities:
        self.calls.append((project_config, tuple(folders)))
        self.log.append("prepare")
        if self.error is not None:
            raise self.error
        folder = self.root / f"run-{len(self.calls)}"
        folder.mkdir(parents=True)
        document = folder / "capabilities.json"
        document.write_text("{}", encoding="ascii")
        prepared = PreparedCapabilities(
            document=document,
            folder=folder,
            digest=DIGEST,
            plugins=2,
            skills=5,
            skills_skipped=1,
            mcp_local=1,
            mcp_remote=1,
            notices=("a project key was ignored",),
        )
        self.prepared.append(prepared)
        return prepared

    def release(self, prepared: PreparedCapabilities) -> None:
        self.log.append("release")
        self.released.append(prepared)
        shutil.rmtree(prepared.folder)

    def sweep(self) -> PruneReport:
        raise AssertionError("a BUILD run never sweeps")


class _Ledger:
    def __init__(self, log: list[str]) -> None:
        self.log = log
        self.calls: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        event: EngineEvent = kwargs["event"]
        self.log.append(f"record:{event.kind}")
        self.calls.append(kwargs)

    def of(self, kind: str) -> list[dict[str, Any]]:
        return [call for call in self.calls if call["event"].kind == kind]


class _Engine(ScriptedEngine):
    """Keeps every spec and the argv `build_argv` makes of it, and writes each start into the
    shared log."""

    log: list[str]
    specs: list[RunSpec]
    argvs: list[tuple[str, ...]]

    async def start(self, spec: RunSpec) -> RunHandle:
        self.log.append("start")
        self.specs = [*getattr(self, "specs", []), spec]
        self.argvs = [*getattr(self, "argvs", []), build_argv(self.descriptor, spec)]
        return await super().start(spec)


class _Harness:
    def __init__(
        self,
        tmp_path: Path,
        *,
        descriptor: EngineDescriptor = CLAUDELOOP,
        error: BaseException | None = None,
        engine: ScriptedEngine | None = None,
        inputs: RunInputsInterface | None = None,
        wind_down: Any = None,
    ) -> None:
        self.tmp = tmp_path
        self.log: list[str] = []
        self.capabilities = _Capabilities(tmp_path / "snapshots", self.log, error)
        self.ledger = _Ledger(self.log)
        if engine is None:
            engine = _Engine(descriptor=descriptor, base_dir=tmp_path / "engine")
        engine.log = self.log  # type: ignore[attr-defined]
        self.engine = engine
        self.handler = BuildImplementHandler(
            worktrees=FakeWorktrees(tmp_path / "worktrees"),
            provisioner=FakeProvisioner(),
            engine=engine,
            ledger=self.ledger,
            jobs=FakeJobRepository(),
            clock=FixedClock(),
            inputs=inputs,
            wind_down=wind_down,
            capabilities=self.capabilities,
        )

    async def run(self, payload: dict[str, object] | None = None) -> Any:
        job = replace(
            make_job(uuid4()),
            kind="build.implement",
            work_item_id="item-1",
            attempts=1,
            payload=payload or {"title": "do the thing"},
        )
        return await handle_leased(self.handler, job)

    @property
    def worktree(self) -> Path:
        return self.tmp / "worktrees" / "item-1"


async def test_the_event_is_recorded_before_the_engine_starts(tmp_path: Path) -> None:
    harness = _Harness(tmp_path)

    outcome = await harness.run()

    assert isinstance(outcome, Success)
    assert harness.log[:3] == ["prepare", f"record:{SNAPSHOTTED}", "start"]
    assert harness.log[-1] == "release"
    [call] = harness.ledger.of(SNAPSHOTTED)
    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert call["engine_id"] == CLAUDELOOP.engine_id
    assert call["causation_id"] == spec.run_id
    assert call["event"].payload == LOOP_CAPABILITIES_RECORD.payload(
        run_id=spec.run_id,
        digest=DIGEST,
        plugins=2,
        skills=5,
        skills_skipped=1,
        mcp_local=1,
        mcp_remote=1,
        notices=1,
    )
    # The notice's text is logged by the service, never recorded.
    assert "a project key was ignored" not in str(call["event"].payload)
    # The project's own file is the only project input, and it may only narrow.
    assert harness.capabilities.calls == [(harness.worktree / "vibey.toml", ())]


@pytest.mark.parametrize("descriptor", [CLAUDELOOP, CLAUDELOOP_LOCAL], ids=lambda d: d.binary)
async def test_the_argv_carries_the_capabilities_flag_and_document(
    tmp_path: Path, descriptor: EngineDescriptor
) -> None:
    harness = _Harness(tmp_path, descriptor=descriptor)

    await harness.run()

    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    [argv] = harness.engine.argvs  # type: ignore[attr-defined]
    [prepared] = harness.capabilities.prepared
    assert spec.capabilities_file == prepared.document
    at = argv.index("--capabilities")
    assert argv[at + 1] == str(prepared.document)


@pytest.mark.parametrize(
    "error",
    [UnlockedMarketplaceError("acme"), LockMismatchError("acme")],
    ids=["unlocked", "lock-mismatch"],
)
async def test_an_unresolvable_snapshot_parks_and_never_starts_the_engine(
    tmp_path: Path, error: Exception
) -> None:
    harness = _Harness(tmp_path, error=error)

    outcome = await harness.run()

    assert isinstance(outcome, Park)
    assert outcome.request.kind == LOOP_CAPABILITIES_GATE_KIND
    assert str(error) in outcome.request.prompt
    assert "vibey loops marketplace update acme" in outcome.request.prompt
    assert "start" not in harness.log
    assert harness.ledger.of(SNAPSHOTTED) == []
    assert harness.capabilities.released == []


@pytest.mark.parametrize(
    "error",
    [
        ConfigError("/person/vibey.toml", "loops.builtin_web must be true or false"),
        SnapshotDocumentError("the capability document cannot be written at /x"),
    ],
    ids=["config", "document"],
)
async def test_a_bad_loops_table_parks(tmp_path: Path, error: Exception) -> None:
    harness = _Harness(tmp_path, error=error)

    outcome = await harness.run()

    assert isinstance(outcome, Park)
    assert outcome.request.kind == LOOP_CAPABILITIES_GATE_KIND
    assert str(error) in outcome.request.prompt
    assert "start" not in harness.log


async def test_a_snapshot_that_cannot_be_written_for_the_os_is_a_retry(tmp_path: Path) -> None:
    harness = _Harness(tmp_path, error=PermissionError("the snapshot folder is not writable"))

    outcome = await harness.run()

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.VIBEY
    assert "the snapshot folder is not writable" in outcome.detail
    assert "start" not in harness.log


@pytest.mark.parametrize("descriptor", [GPTOSSLOOP, CODEXLOOP], ids=lambda d: d.binary)
async def test_an_engine_without_the_flag_is_given_no_snapshot_and_no_event(
    tmp_path: Path, descriptor: EngineDescriptor
) -> None:
    harness = _Harness(tmp_path, descriptor=descriptor)

    outcome = await harness.run()

    assert isinstance(outcome, Success)
    assert harness.capabilities.calls == []
    assert harness.ledger.of(SNAPSHOTTED) == []
    [spec] = harness.engine.specs  # type: ignore[attr-defined]
    assert spec.capabilities_file is None
    [argv] = harness.engine.argvs  # type: ignore[attr-defined]
    assert "--capabilities" not in argv


async def test_without_a_capability_service_a_claudeloop_run_is_as_before(
    tmp_path: Path,
) -> None:
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
    assert engine.specs[0].capabilities_file is None


class _FailingStart(_Engine):
    async def start(self, spec: RunSpec) -> RunHandle:
        self.log.append("start")
        raise RuntimeError("the runner could not be spawned")


async def test_the_snapshot_folder_is_removed_on_success_failure_and_wind_down(
    tmp_path: Path,
) -> None:
    # Success.
    success = _Harness(tmp_path / "success")
    assert isinstance(await success.run(), Success)
    # Failure: a run that never reports completion.
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
    # Wind-down: exit 75 hands the run to the orchestrator.
    wind_down = _RecordingWindDown()
    winding = _Harness(
        tmp_path / "wind-down",
        engine=_Engine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "wind-down-engine",
            script=_wind_down_script(),
            exit_code_script=[75],
        ),
        wind_down=wind_down,
    )
    assert await winding.run() == Success({"wind_down": True})
    assert len(wind_down.calls) == 1

    for harness in (success, failing, winding):
        [prepared] = harness.capabilities.prepared
        assert harness.capabilities.released == [prepared]
        assert not prepared.folder.exists()
        assert harness.log[-1] == "release"


async def test_the_snapshot_folder_is_removed_when_the_engine_cannot_start(
    tmp_path: Path,
) -> None:
    harness = _Harness(
        tmp_path, engine=_FailingStart(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    )
    with pytest.raises(RuntimeError, match="could not be spawned"):
        await harness.run()
    [prepared] = harness.capabilities.prepared
    assert harness.capabilities.released == [prepared]
    assert harness.log == ["prepare", f"record:{SNAPSHOTTED}", "start", "release"]


@pytest.mark.parametrize("with_file", [True, False], ids=["file-and-paste", "paste-only"])
async def test_the_input_folder_is_in_the_documents_folders(
    tmp_path: Path, with_file: bool
) -> None:
    world = _InputsWorld(tmp_path)
    await world.add("paste", "paste", b"Use the blue theme.")
    if with_file:
        await world.add("file", "spec.md", b"# Spec\n")
    harness = _Harness(tmp_path / "run", inputs=world.inputs)
    # The inputs world's project is the job's project.
    job = replace(world.job, payload={"title": "do the thing"})

    outcome = await handle_leased(harness.handler, job)

    assert isinstance(outcome, Success)
    run_id = UUID(str(outcome.result["run_id"]))
    inputs = harness.worktree / ".vibey" / "inputs" / str(run_id)
    assert (inputs / "paste.md").is_file()
    assert (inputs / "attachments" / "spec.md").is_file() is with_file
    assert harness.capabilities.calls == [(harness.worktree / "vibey.toml", (inputs,))]
    assert inputs.is_absolute()


async def test_with_no_inputs_the_documents_folders_are_empty(tmp_path: Path) -> None:
    world = _InputsWorld(tmp_path)
    harness = _Harness(tmp_path / "run", inputs=world.inputs)
    job = replace(world.job, payload={"title": "do the thing"})

    assert isinstance(await handle_leased(harness.handler, job), Success)

    assert harness.capabilities.calls == [(harness.worktree / "vibey.toml", ())]


async def test_a_wind_down_follow_up_is_given_a_fresh_snapshot_and_the_seed_is_unchanged(
    tmp_path: Path,
) -> None:
    harness = _Harness(tmp_path)

    first = await harness.run({"seed_prompt": SEED})
    second = await harness.run({"seed_prompt": SEED})

    assert isinstance(first, Success) and isinstance(second, Success)
    specs: list[RunSpec] = harness.engine.specs  # type: ignore[attr-defined]
    for spec in specs:
        assert spec.prompt.startswith(SEED)  # the gate-verified seed, byte for byte
        assert spec.prompt == SEED
    documents = [spec.capabilities_file for spec in specs]
    assert documents == [prepared.document for prepared in harness.capabilities.prepared]
    assert documents[0] != documents[1]  # each follow-up is given its own, freshly resolved
    assert len(harness.ledger.of(SNAPSHOTTED)) == 2
    assert harness.capabilities.released == harness.capabilities.prepared
