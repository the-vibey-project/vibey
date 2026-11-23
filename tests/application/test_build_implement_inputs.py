# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One input path into every BUILD run (SP-LOOPS Phase 3, Task 6; design Goal 4).

The BUILD handler runs with the real run inputs service over the real store in pytest's
temporary folder and a scripted engine that keeps the prompt it was started with. Every engine
reads the run's prompt and its worktree, so what reaches this engine is what reaches each loop.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from tests.application.fakes import FakeJobRepository, handle_leased, make_job
from tests.application.test_build_implement_handler import (
    FakeLedger,
    FakeProvisioner,
    FakeWorktrees,
    FixedClock,
)
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.dto import (
    EngineEvent,
    JobRecord,
    ProjectRecord,
    RunHandle,
    RunInputs,
    RunSpec,
)
from vibey.application.interfaces.run_inputs_interface import RunInputsInterface
from vibey.application.run_inputs_service import RunInputsService
from vibey.application.worker import Failure, Success
from vibey.domain.config import ConfigError
from vibey.domain.errors import InputStoreError
from vibey.domain.job import FailureClass
from vibey.domain.phase import Phase
from vibey.domain.run_input import InputKind, InputListing, RunInput, RunInputsSettings
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine
from vibey.infrastructure.inputs.hash_addressed_input_store import HashAddressedInputStore
from vibey.infrastructure.inputs.no_follow_files import NoFollowFiles

AT = datetime(2026, 11, 23, tzinfo=UTC)


class _PromptEngine(ScriptedEngine):
    """A scripted engine that keeps every run's spec, and how many runs it was started for."""

    specs: list[RunSpec]

    async def start(self, spec: RunSpec) -> RunHandle:
        self.specs = [*getattr(self, "specs", []), spec]
        return await super().start(spec)


class _Projects:
    def __init__(self, record: ProjectRecord) -> None:
        self._record = record

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._record if project_id == self._record.project_id else None


class _Ledger:
    def __init__(self) -> None:
        self.job_ids: list[UUID | None] = []

    async def record(
        self, *, project_id: UUID, cycle: int, event: EngineEvent, job_id: UUID | None = None
    ) -> None:
        self.job_ids.append(job_id)


class _World:
    def __init__(self, tmp_path: Path) -> None:
        self.tmp = tmp_path
        self.job: JobRecord = replace(
            make_job(uuid4()), kind="build.implement", work_item_id="item-1", attempts=1
        )
        repo = tmp_path / "repo"
        repo.mkdir()
        record = ProjectRecord(
            project_id=self.job.project_id,
            name="greeter",
            repo_path=repo,
            phase=Phase.BUILD,
            cycle=self.job.cycle,
            max_cycles=3,
            config={},
            created_at=AT,
            updated_at=AT,
        )
        self.ledger = _Ledger()
        self.store = HashAddressedInputStore(tmp_path / "state" / "inputs", FixedClock())
        self.projects = _Projects(record)
        self.inputs = RunInputsService(
            store=self.store,
            projects=self.projects,
            ledger=self.ledger,
            clock=FixedClock(),
            limits=RunInputsSettings,
            writer=NoFollowFiles(),
        )

    async def add(self, kind: InputKind, name: str, data: bytes) -> None:
        await self.inputs.add(self.job.project_id, kind, name, data)

    async def run(
        self, *, inputs: RunInputsInterface | None, payload: dict[str, object] | None = None
    ) -> tuple[object, _PromptEngine, Path]:
        engine = _PromptEngine(descriptor=CLAUDELOOP, base_dir=self.tmp / "engine")
        worktrees = FakeWorktrees(self.tmp / "worktrees")
        handler = BuildImplementHandler(
            worktrees=worktrees,
            provisioner=FakeProvisioner(),
            engine=engine,
            ledger=FakeLedger(),
            jobs=FakeJobRepository(),
            clock=FixedClock(),
            inputs=inputs,
        )
        job = replace(self.job, payload=payload or {"title": "do the thing"})
        outcome = await handle_leased(handler, job)
        return outcome, engine, self.tmp / "worktrees" / "item-1"


async def test_a_build_run_gets_the_paste_in_its_prompt_and_the_file_in_its_worktree(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    await world.add("paste", "paste", b"Use the blue theme.")
    await world.add("file", "spec.md", b"# Spec\n")

    outcome, engine, worktree = await world.run(inputs=world.inputs)

    assert isinstance(outcome, Success)
    [spec] = engine.specs
    run_id = UUID(str(outcome.result["run_id"]))
    assert spec.run_id == run_id
    given = await world.inputs.materialize(world.job.project_id, run_id, worktree)
    assert spec.prompt.endswith(given.prompt_section)
    assert "Use the blue theme." in spec.prompt
    attachment = worktree / ".vibey" / "inputs" / str(run_id) / "attachments" / "spec.md"
    assert attachment.read_bytes() == b"# Spec\n"


async def test_with_no_inputs_the_prompt_is_byte_identical_to_before(tmp_path: Path) -> None:
    world = _World(tmp_path)
    _, without, _ = await world.run(inputs=None)
    _, with_service, worktree = await world.run(inputs=world.inputs)
    assert with_service.specs[0].prompt == without.specs[0].prompt
    assert not (worktree / ".vibey" / "inputs").exists()


async def test_a_wind_down_seed_reaches_the_engine_verbatim_and_the_files_are_still_there(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    await world.add("paste", "paste", b"pasted words")
    await world.add("file", "spec.md", b"bytes")
    seed = "Objective: resume without losing [q-77]."

    outcome, engine, worktree = await world.run(inputs=world.inputs, payload={"seed_prompt": seed})

    assert isinstance(outcome, Success)
    assert engine.specs[0].prompt == seed
    run_id = outcome.result["run_id"]
    assert (worktree / ".vibey" / "inputs" / str(run_id) / "paste.md").is_file()
    assert (worktree / ".vibey" / "inputs" / str(run_id) / "attachments" / "spec.md").is_file()


class _RefusingInputs:
    """Inputs that cannot be given: a worktree whose `.vibey` is a symlink, say."""

    async def add(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        raise AssertionError("not called")

    async def listed(self, project_id: UUID) -> InputListing:
        raise AssertionError("not called")

    async def materialize(
        self, project_id: UUID, run_id: UUID, worktree_path: Path, *, job_id: UUID | None = None
    ) -> RunInputs:
        raise InputStoreError(f"{worktree_path}/.vibey: is a symlink or not a folder")


async def test_inputs_that_cannot_be_given_fail_the_run_before_any_engine_session(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    outcome, engine, _ = await world.run(inputs=_RefusingInputs())
    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.VIBEY
    assert "run inputs" in outcome.detail
    assert "symlink" in outcome.detail
    assert getattr(engine, "specs", []) == []


async def test_limits_that_cannot_be_read_fail_the_run_before_any_engine_session(
    tmp_path: Path,
) -> None:
    world = _World(tmp_path)
    await world.add("paste", "paste", b"words")

    def unreadable() -> RunInputsSettings:
        raise ConfigError("/home/person/.config/vibey/vibey.toml", "max_items must be positive")

    broken = RunInputsService(
        store=world.store,
        projects=world.projects,
        ledger=_Ledger(),
        clock=FixedClock(),
        limits=unreadable,
        writer=NoFollowFiles(),
    )
    outcome, engine, _ = await world.run(inputs=broken)
    assert isinstance(outcome, Failure)
    assert "max_items must be positive" in outcome.detail
    assert getattr(engine, "specs", []) == []


async def test_the_run_event_is_recorded_under_the_build_jobs_id(tmp_path: Path) -> None:
    world = _World(tmp_path)
    await world.add("paste", "paste", b"words")
    await world.run(inputs=world.inputs)
    assert world.ledger.job_ids == [None, world.job.id]


async def test_a_store_root_that_cannot_be_read_fails_the_run_before_the_engine_starts(
    tmp_path: Path,
) -> None:
    # Re-review N7: a project with index rows whose store root the worker cannot read fails
    # loudly before engine.start, never starting with no inputs.
    world = _World(tmp_path)
    await world.add("paste", "paste", b"words")
    root = tmp_path / "state" / "inputs"
    root.rename(tmp_path / "state" / "moved")
    root.write_bytes(b"a file where the store root belongs")
    outcome, engine, _ = await world.run(inputs=world.inputs)
    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.VIBEY
    assert "the run inputs could not be given to the run" in outcome.detail
    assert getattr(engine, "specs", []) == []
