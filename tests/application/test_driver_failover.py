# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The driver failover service, both directions, against in-memory seams (ADR-0070)."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest

from vibey.application.driver_failover import DriverFailoverService
from vibey.application.dto import (
    DriverSignal,
    ProcessResult,
    RepoSnapshot,
    TranscriptDigest,
)
from vibey.application.interfaces.driver import (
    DriverFailoverServiceInterface,
    DriverLedgerPort,
    DriverWorkspacePort,
    ProcessPort,
)
from vibey.domain.failover import FailoverKind, FailoverRecord, FailoverSettings

T0 = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
CWD = "/work/tree"


@dataclass
class Clock:
    at: datetime = T0

    def now(self) -> datetime:
        return self.at


@dataclass
class Workspace:
    """Digests are served from a script, one per read; the last one repeats."""

    digests: list[TranscriptDigest | None] = field(
        default_factory=lambda: [TranscriptDigest("d1", 10)]
    )
    copy_digest: TranscriptDigest | None = field(default_factory=lambda: TranscriptDigest("c1", 10))
    head: str = "cafe"
    commits: tuple[str, ...] = ("beef feat: more",)
    briefs: dict[str, str] = field(default_factory=dict)
    copies: list[str] = field(default_factory=list)

    def digest(self, path: str) -> TranscriptDigest | None:
        if path in self.copies:
            return self.copy_digest
        return self.digests.pop(0) if len(self.digests) > 1 else self.digests[0]

    def copy_transcript(self, path: str, cwd: str, name: str) -> str:
        copy = f"{cwd}/.vibey/driver/{name}"
        self.copies.append(copy)
        return copy

    def repo(self, cwd: str) -> RepoSnapshot:
        return RepoSnapshot(branch="feat/x", head_sha=self.head, dirty_paths=("a.py",))

    def commits_since(self, cwd: str, sha: str) -> tuple[str, ...]:
        return self.commits

    def write_brief(self, cwd: str, name: str, text: str) -> str:
        path = f"{cwd}/.vibey/driver/{name}"
        self.briefs[path] = text
        return path


@dataclass
class Ledger:
    rows: list[FailoverRecord] = field(default_factory=list)

    def records(self) -> tuple[FailoverRecord, ...]:
        return tuple(self.rows)

    def append(self, kind: FailoverKind, *, at: datetime, payload: Mapping[str, object]) -> None:
        self.rows.append(FailoverRecord(kind=kind, at=at, payload=dict(payload)))


@dataclass
class Processes:
    results: list[ProcessResult] = field(
        default_factory=lambda: [
            ProcessResult(0, '{"is_error": false, "subtype": "success"}'),
            ProcessResult(0, ""),
        ]
    )
    spawned: list[tuple[str, ...]] = field(default_factory=list)
    ran: list[tuple[str, ...]] = field(default_factory=list)

    def spawn(self, argv: Sequence[str], *, cwd: str) -> None:
        self.spawned.append(tuple(argv))

    def run(self, argv: Sequence[str], *, cwd: str, timeout: float) -> ProcessResult:
        self.ran.append(tuple(argv))
        return self.results.pop(0)


SIGNAL = DriverSignal(
    session_id="sess-1234-5678",
    transcript_path="/home/.claude/projects/p/sess.jsonl",
    cwd=CWD,
    error="billing_error",
    last_message="API Error: credit balance too low",
)


def _service(
    *,
    workspace: Workspace | None = None,
    ledger: Ledger | None = None,
    processes: Processes | None = None,
    clock: Clock | None = None,
    settings: FailoverSettings | None = None,
) -> tuple[DriverFailoverService, Workspace, Ledger, Processes, Clock]:
    ws, lg, pr, ck = (
        workspace or Workspace(),
        ledger or Ledger(),
        processes or Processes(),
        clock or Clock(),
    )
    service = DriverFailoverService(
        settings=settings or FailoverSettings(),
        workspace=ws,
        ledger=lg,
        processes=pr,
        clock=ck,
    )
    return service, ws, lg, pr, ck


def test_the_fakes_and_service_satisfy_the_ports() -> None:
    service, ws, lg, pr, _ = _service()
    assert isinstance(service, DriverFailoverServiceInterface)
    assert isinstance(ws, DriverWorkspacePort)
    assert isinstance(lg, DriverLedgerPort)
    assert isinstance(pr, ProcessPort)


def test_a_non_capacity_error_is_ignored() -> None:
    service, _, ledger, processes, _ = _service()
    outcome = service.fail_over(DriverSignal("s", "/t", CWD, error="overloaded"))
    assert outcome.result == "ignored"
    assert ledger.rows == [] and processes.spawned == []


def test_credits_fail_over_to_gptossloop_at_ultra_after_the_gate() -> None:
    service, workspace, ledger, processes, _ = _service()
    outcome = service.fail_over(SIGNAL)
    assert outcome.result == "failed_over"
    assert outcome.status is not None and outcome.status.active
    (record,) = ledger.rows
    assert record.kind is FailoverKind.FAILED_OVER
    assert record.payload["cause"] == "credits"
    assert record.payload["target"] == "gptossloop"
    assert record.payload["effort"] == "ULTRA"
    assert record.payload["gate_mode"] == "strict"
    assert record.payload["transcript_digest"] == "d1"
    assert record.payload["probe_not_before"] == (T0 + timedelta(minutes=30)).isoformat()
    assert "resets_at" not in record.payload
    (argv,) = processes.spawned
    assert argv[:2] == ("gptossloop", "run")
    assert argv[2] == outcome.brief_path and argv[-1] == CWD
    assert argv[4] == record.payload["run_id"] == outcome.detail
    assert "sha256 `d1`" in workspace.briefs[str(outcome.brief_path)]


def test_a_second_hook_for_an_active_failover_starts_nothing() -> None:
    service, _, ledger, processes, _ = _service()
    service.fail_over(SIGNAL)
    again = service.fail_over(SIGNAL)
    assert again.result == "already"
    assert len(ledger.rows) == 1 and len(processes.spawned) == 1


def test_a_moving_transcript_escalates_to_full_transcript() -> None:
    moving = [TranscriptDigest(f"d{n}", n) for n in range(1, 8)] + [TranscriptDigest("z", 9)]
    service, workspace, ledger, _, _ = _service(workspace=Workspace(digests=moving))
    outcome = service.fail_over(SIGNAL)
    assert outcome.result == "failed_over"
    assert ledger.rows[0].payload["gate_mode"] == "full_transcript"
    assert ledger.rows[0].payload["gate_attempts"] == 4
    assert ledger.rows[0].payload["transcript_digest"] == "c1"
    assert workspace.copies and workspace.copies[0].endswith(".jsonl")


def test_an_unreadable_transcript_parks_and_starts_nothing() -> None:
    service, workspace, ledger, processes, _ = _service(workspace=Workspace(digests=[None]))
    outcome = service.fail_over(SIGNAL)
    assert outcome.result == "parked"
    assert "R6: transcript unreadable" in outcome.detail
    assert outcome.brief_path is not None and "PARKED-failover" in outcome.brief_path
    assert workspace.briefs[outcome.brief_path].startswith("# PARKED")
    assert ledger.rows == [] and processes.spawned == [] and workspace.copies == []


def test_an_unreadable_copy_parks() -> None:
    moving = [TranscriptDigest(f"d{n}", n) for n in range(1, 9)]
    ws = Workspace(digests=moving, copy_digest=None)
    service, _, ledger, _, _ = _service(workspace=ws)
    assert service.fail_over(SIGNAL).result == "parked"
    assert ledger.rows == []


def test_probe_is_idle_without_a_failover() -> None:
    service, _, _, processes, _ = _service()
    assert service.probe(CWD).result == "idle"
    assert processes.ran == []


def test_probe_waits_for_its_schedule() -> None:
    service, _, ledger, processes, _ = _service()
    service.fail_over(SIGNAL)
    assert service.probe(CWD).result == "not_due"
    assert processes.ran == [] and len(ledger.rows) == 1


@pytest.mark.parametrize(
    ("result", "detail"),
    [
        (ProcessResult(1, ""), "exit 1"),
        (ProcessResult(0, "not json"), "the probe printed no JSON result"),
        (ProcessResult(0, '{"is_error": true}'), "the probe's result is an error"),
        (ProcessResult(0, "[1]"), "the probe's result is an error"),
    ],
)
def test_a_failed_probe_is_recorded_and_hands_nothing_back(
    result: ProcessResult, detail: str
) -> None:
    clock = Clock()
    service, _, ledger, processes, _ = _service(processes=Processes(results=[result]), clock=clock)
    service.fail_over(SIGNAL)
    clock.at = T0 + timedelta(hours=1)
    outcome = service.probe(CWD)
    assert outcome.result == "probe_failed" and outcome.detail == detail
    assert [r.kind for r in ledger.rows] == [FailoverKind.FAILED_OVER, FailoverKind.PROBED]
    assert ledger.rows[1].payload["ok"] is False
    assert len(processes.spawned) == 1


def test_a_recorded_successful_probe_hands_back_to_the_same_session() -> None:
    clock = Clock()
    service, workspace, ledger, processes, _ = _service(clock=clock)
    service.fail_over(SIGNAL)
    run_id = str(ledger.rows[0].payload["run_id"])
    clock.at = T0 + timedelta(hours=1)
    outcome = service.probe(CWD)
    assert outcome.result == "handed_back" and outcome.detail == SIGNAL.session_id
    assert [r.kind for r in ledger.rows] == [
        FailoverKind.FAILED_OVER,
        FailoverKind.PROBED,
        FailoverKind.HANDED_BACK,
    ]
    assert ledger.rows[1].payload == {"ok": True, "exit_code": 0, "detail": "success"}
    assert ledger.rows[2].payload["probe_at"] == clock.at.isoformat()
    assert processes.ran[0][0] == "claude"
    assert processes.ran[1] == ("gptossloop", "wind-down", run_id, "--cwd", CWD)
    resume = processes.spawned[-1]
    assert resume[:4] == ("claude", "-p", "--resume", SIGNAL.session_id)
    assert str(outcome.brief_path) in resume[4]
    text = workspace.briefs[str(outcome.brief_path)]
    assert "handback brief" in text and "- beef feat: more" in text
    assert outcome.status is not None and not outcome.status.active
    assert service.probe(CWD).result == "idle"


def test_a_probe_recorded_before_a_crash_is_not_rerun() -> None:
    ledger = Ledger()
    clock = Clock(at=T0 + timedelta(hours=1))
    service, _, _, processes, _ = _service(
        ledger=ledger, clock=clock, processes=Processes(results=[ProcessResult(0, "")])
    )
    ledger.rows += [
        FailoverRecord(FailoverKind.FAILED_OVER, T0, {"session_id": "s", "run_id": "r"}),
        FailoverRecord(FailoverKind.PROBED, T0 + timedelta(minutes=40), {"ok": True}),
    ]
    assert service.probe(CWD).result == "handed_back"
    assert [argv[1] for argv in processes.ran] == ["wind-down"]


def test_a_handback_that_fails_its_gate_parks_and_resumes_nothing() -> None:
    ledger = Ledger()
    ws = Workspace(digests=[None])
    service, workspace, _, processes, _ = _service(workspace=ws, ledger=ledger)
    ledger.rows += [
        FailoverRecord(FailoverKind.FAILED_OVER, T0, {"session_id": "s", "run_id": "r"}),
        FailoverRecord(FailoverKind.PROBED, T0, {"ok": True}),
    ]
    outcome = service.probe(CWD)
    assert outcome.result == "parked"
    assert outcome.brief_path is not None and "PARKED-handback" in outcome.brief_path
    assert processes.spawned == [] and processes.ran == []
    assert len(ledger.rows) == 2


def test_status_reads_the_ledger() -> None:
    service, _, _, _, _ = _service()
    assert not service.status().active
    service.fail_over(SIGNAL)
    assert service.status().active


def test_argv_templates_pass_other_braces_through() -> None:
    settings = FailoverSettings(sovereign_argv=("run", "{cwd}", "{literal}", "{prompt}"))
    service, _, _, processes, _ = _service(settings=settings)
    service.fail_over(SIGNAL)
    assert processes.spawned == [("run", CWD, "{literal}", "")]
