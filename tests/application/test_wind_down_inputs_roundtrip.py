# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A handed-off run sees the same input section as the run it replaces (SP-LOOPS Phase 3c,
Task 7; operator ruling OR-5).

The outgoing BUILD run is given inputs, which the ledger records under its job. It winds down:
the wind-down orchestrator pins those digests into the follow-up's payload beside the seed the
no-loss gate verified, and the follow-up's run is given exactly them, its prompt the seed byte for
byte with the same input section after it. Real run inputs service and local store in pytest's
folder; the ledger is one in-memory list both sides read and write. No network, no thread.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from tests.application.fakes import make_job
from tests.application.test_wind_down import _STOP, _ledger_events, _orchestrator
from vibey.application.dto import EngineEvent, ProjectRecord
from vibey.application.run_inputs_service import RunInputsService
from vibey.application.seed_prompt import render_seed_prompt
from vibey.application.worker import Success
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.input_ledger import INPUT_LEDGER, RecordedInputs
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.run_input import HANDOFF_INPUTS_KEY, RunInputsSettings
from vibey.infrastructure.inputs.hash_addressed_input_store import HashAddressedInputStore
from vibey.infrastructure.inputs.no_follow_files import NoFollowFiles

AT = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class _Clock:
    def now(self) -> datetime:
        return AT


class _SharedLedger:
    """The run inputs' ledger port over a list of `LedgerEvent`s the wind-down also reads."""

    def __init__(self, project_id: UUID, events: list[LedgerEvent]) -> None:
        self._project_id = project_id
        self.events = events

    async def record(
        self, *, project_id: UUID, cycle: int, event: EngineEvent, job_id: UUID | None = None
    ) -> None:
        payload = dict(event.payload)
        self.events.append(
            LedgerEvent(
                event_id=uuid4(),
                project_id=project_id,
                cycle=1,
                phase=Phase.BUILD,
                seq=max((e.seq for e in self.events), default=0) + 1,
                kind=EventKind.ARTIFACT_PRODUCED,
                engine_id=None,
                job_id=job_id,
                causation_id=None,
                correlation_id=uuid4(),
                provenance=Provenance.TRUSTED,
                produced_at=AT,
                payload=payload,
                digest=digest_event(payload),
            )
        )

    async def added(self, project_id: UUID) -> RecordedInputs:
        return INPUT_LEDGER.recorded((e.seq, e.payload) for e in self.events)


class _Projects:
    def __init__(self, record: ProjectRecord) -> None:
        self._record = record

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self._record


def _service(tmp_path: Path, project_id: UUID, ledger: _SharedLedger) -> RunInputsService:
    record = ProjectRecord(
        project_id=project_id,
        name="greeter",
        repo_path=tmp_path,
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=AT,
        updated_at=AT,
    )
    return RunInputsService(
        store=HashAddressedInputStore(tmp_path / "state" / "inputs", _Clock()),
        projects=_Projects(record),
        ledger=ledger,
        clock=_Clock(),
        limits=RunInputsSettings,
        writer=NoFollowFiles(),
    )


async def test_a_handed_off_run_sees_the_same_input_section_as_the_run_it_replaces(
    tmp_path: Path,
) -> None:
    project_id = uuid4()
    events: list[LedgerEvent] = list(_ledger_events(project_id, question_text="cap at 5?"))
    ledger = _SharedLedger(project_id, events)
    service = _service(tmp_path, project_id, ledger)
    await service.add(project_id, "paste", "paste", b"Use the blue theme.")
    await service.add(project_id, "file", "spec.md", b"# Spec\n")

    outgoing_job = replace(
        make_job(project_id),
        project_id=project_id,
        kind="build.implement",
        work_item_id="wi-1",
        attempts=1,
        payload={"title": "outbox relay"},
    )
    outgoing_tree = tmp_path / "outgoing"
    outgoing_tree.mkdir()
    outgoing_run = uuid4()
    outgoing = await service.materialize(
        project_id, outgoing_run, outgoing_tree, job_id=outgoing_job.id
    )
    # An input added after the outgoing run started: not part of what it was given.
    await service.add(project_id, "paste", "paste", b"added after the handoff")

    orchestrator, handoffs, jobs, _ = await _orchestrator(project_id, tuple(events))
    outcome = await orchestrator.execute(
        job=outgoing_job,
        worktree_path=tmp_path / "handoff",
        engine_id=EngineId.CLAUDELOOP,
        effort=Effort.LOW,
        stop=_STOP,
    )
    assert isinstance(outcome, Success)
    (envelope,) = handoffs.envelopes
    assert envelope.gate.ok  # the gate passed with the input events in its range
    follow_up = next(j for j in jobs._jobs.values() if j.state is JobState.READY)
    assert follow_up.payload["seed_prompt"] == render_seed_prompt(envelope.brief)
    pin = follow_up.payload[HANDOFF_INPUTS_KEY]
    assert pin == list(outgoing.digests)

    incoming_tree = tmp_path / "incoming"
    incoming_tree.mkdir()
    incoming_run = uuid4()
    incoming = await service.materialize(
        project_id, incoming_run, incoming_tree, job_id=follow_up.id, pinned=tuple(pin)
    )
    # The same section, its run folder named for the incoming run.
    assert incoming.prompt_section == outgoing.prompt_section.replace(
        str(outgoing_run), str(incoming_run)
    )
    assert incoming.digests == outgoing.digests
    assert "added after the handoff" not in incoming.prompt_section
