# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for the storm's lane watchdog: a lane cannot hang the storm.

Lanes run strictly one at a time (sub-doctrine 8.c: one model slot), so one hung lane stops
the whole storm. On 2026-09-23 a run went silent at 09:17:39Z and nothing noticed until a
human restarted the storm at 10:50Z; four runs on disk have no terminal event at all, so
every downstream tool reads their outcome as unknown. These tests pin the three things that
make that impossible: a wall-clock limit per attempt and per lane, a stall watchdog, and a
terminal event written for every run the watchdog ends.

The children here are tiny Python scripts that sleep, stop writing events, or spawn a
grandchild in a session of its own -- the shape of qwenloop's shell tool, which is exactly
the process a plain kill of the lane would leave running. Every limit is a fraction of a
second, declared through `LaneLimits` the same way `storm.toml` declares the real ones.

The tools are addressed by path for the reason `test_storm_check_parser.py` gives: they are
scripts, not a package. Delete this in the same commit that deletes them.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from unittest import mock

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, filename: str):  # noqa: ANN202 - a module object
    spec = importlib.util.spec_from_file_location(name, TOOLS / filename)
    assert spec and spec.loader, f"the storm tool is missing: {TOOLS / filename}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lane_watchdog = _load("lane_watchdog", "lane_watchdog.py")
LaneLimits = lane_watchdog.LaneLimits

#: Small enough to keep the file fast, large enough that a loaded CI runner still starts a
#: Python child and sees it write before the stall limit fires.
FAST = LaneLimits(
    attempt_seconds=5.0,
    lane_seconds=30.0,
    stall_seconds=1.5,
    poll_seconds=0.05,
    grace_seconds=1.0,
)
#: For children expected to finish by themselves: a slow runner starting Python must not be
#: mistaken for a stall.
PATIENT = LaneLimits(
    attempt_seconds=60.0,
    lane_seconds=120.0,
    stall_seconds=30.0,
    poll_seconds=0.05,
    grace_seconds=1.0,
)


def child(tmp_path: Path, body: str) -> list[str]:
    """argv for a fake attempt. `body` runs with the run's EVENTS file, `event()` to append to
    it, and the private report channel the real child uses: `record(pid)` for a subprocess
    it started in a new session, `verdict(...)` for its result."""
    script = tmp_path / f"child-{time.monotonic_ns()}.py"
    script.write_text(
        "import json, os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "spec = json.loads(Path(sys.argv[1]).read_text())\n"
        "EVENTS = Path(spec['events'])\n"
        f"FD = int(os.environ.pop({lane_watchdog.REPORT_FD_ENV!r}))\n"
        "EVENTS.parent.mkdir(parents=True, exist_ok=True)\n"
        "def event(kind, **more):\n"
        "    with EVENTS.open('a') as stream:\n"
        "        stream.write(json.dumps({'type': kind, **more}) + '\\n')\n"
        "def record(pid):\n"
        "    os.write(FD, f'pid {pid}\\n'.encode())\n"
        "def verdict(**found):\n"
        "    os.write(FD, ('result ' + json.dumps(found) + '\\n').encode())\n"
        + textwrap.dedent(body),
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


def gone(pid: int, within: float = 5.0) -> bool:
    """Whether `pid` has stopped existing. Not our child, so it cannot be waited on."""
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        time.sleep(0.05)
    return False


def runner(tmp_path: Path, argv_body: str, limits: LaneLimits = FAST, max_attempts: int = 3):
    lane = tmp_path / "lanes" / "a-lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    argv = child(tmp_path, argv_body)
    return lane, lane_watchdog.LaneAttempts(
        lane,
        slug="a-lane",
        issue=504,
        max_attempts=max_attempts,
        limits=limits,
        progress_log=tmp_path / "progress.log",
        state_dir=tmp_path / "state",
        child_argv=lambda spec: [*argv, str(spec)],
    )


def events_of(lane: Path, run_id: str) -> list[dict]:
    path = lane / ".qwenloop" / "runs" / run_id / "events.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# --- the limits are declared, and the defaults are the measured ones ---------------------


def test_limits_default_to_the_measured_values_when_storm_toml_is_silent(tmp_path: Path) -> None:
    limits = LaneLimits.declared(tmp_path)
    assert limits == LaneLimits(
        attempt_seconds=lane_watchdog.ATTEMPT_SECONDS,
        lane_seconds=lane_watchdog.LANE_SECONDS,
        stall_seconds=lane_watchdog.STALL_SECONDS,
        poll_seconds=lane_watchdog.POLL_SECONDS,
        grace_seconds=lane_watchdog.GRACE_SECONDS,
    )


def test_the_stall_limit_sits_above_the_model_request_timeout() -> None:
    """A model call may legitimately stay silent until qwenloop's own 900 s request timeout,
    and a shell tool call after it for up to 120 s. Killing sooner pre-empts a clean
    `unavailable` with a kill; the stall limit must clear both."""
    assert lane_watchdog.STALL_SECONDS > 900 + 120
    assert lane_watchdog.ATTEMPT_SECONDS > lane_watchdog.STALL_SECONDS
    assert lane_watchdog.LANE_SECONDS > lane_watchdog.ATTEMPT_SECONDS


def test_storm_toml_declares_every_limit(tmp_path: Path) -> None:
    (tmp_path / "storm.toml").write_text(
        "[lane]\n"
        "attempt_timeout_seconds = 60\n"
        "lane_timeout_seconds = 120\n"
        "stall_timeout_seconds = 30\n"
        "watchdog_poll_seconds = 0.5\n"
        "kill_grace_seconds = 2\n",
        encoding="utf-8",
    )
    assert LaneLimits.declared(tmp_path) == LaneLimits(60.0, 120.0, 30.0, 0.5, 2.0)


@pytest.mark.parametrize("value", ['"soon"', "0", "-5", "true", "inf", "-inf", "nan"])
def test_a_limit_that_is_not_a_positive_number_is_refused(tmp_path: Path, value: str) -> None:
    """A limit of zero would kill every attempt at once; a word would silently mean the
    default. Either is a decision the operator did not make, so it stops the lane (10.f)."""
    (tmp_path / "storm.toml").write_text(f"[lane]\nstall_timeout_seconds = {value}\n")
    with pytest.raises(SystemExit, match="stall_timeout_seconds"):
        LaneLimits.declared(tmp_path)


# --- the watchdog ---------------------------------------------------------------------------


def test_an_attempt_that_finishes_is_left_alone(tmp_path: Path) -> None:
    lane, attempts = runner(
        tmp_path,
        """
        event('turn.completed', turn=1)
        event('completed', turn=1)
        verdict(status='completed', turns=1)
        """,
        limits=PATIENT,
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "completed"
    assert record["turns"] == 1
    assert [e["type"] for e in events_of(lane, record["run_id"])] == ["turn.completed", "completed"]
    assert not (tmp_path / "progress.log").exists()


def test_a_silent_run_is_stalled_and_its_whole_process_tree_stopped(tmp_path: Path) -> None:
    """The 2026-09-23 shape: events stop, the process stays. The grandchild runs in a session
    of its own, as qwenloop's shell tool does, so killing the attempt's group alone would
    leave it running; the pid the attempt recorded is how it is reached without `ps`."""
    marker = tmp_path / "grandchild.pid"
    lane, attempts = runner(
        tmp_path,
        f"""
        event('turn.completed', turn=1, ended_at='2026-09-23T09:17:39.098Z')
        tool = subprocess.Popen(['sleep', '600'], start_new_session=True)
        record(tool.pid)
        Path({str(marker)!r}).write_text(str(tool.pid))
        same_group = subprocess.Popen(['sleep', '600'])
        Path({str(marker)!r} + '.group').write_text(str(same_group.pid))
        time.sleep(600)
        """,
    )
    started = time.monotonic()
    record = attempts.run(1, "plan")
    assert time.monotonic() - started < FAST.stall_seconds + FAST.grace_seconds + 3
    assert record["status"] == "stalled"
    assert record["turns"] == 1
    assert gone(int(marker.read_text())), "the tool's own session outlived the lane"
    assert gone(int(Path(str(marker) + ".group").read_text())), "the attempt's group survived"


def test_a_stalled_run_ends_with_a_terminal_event_naming_the_last_event(tmp_path: Path) -> None:
    lane, attempts = runner(tmp_path, "event('turn.completed', turn=1)\ntime.sleep(600)\n")
    record = attempts.run(1, "plan")
    last = events_of(lane, record["run_id"])[-1]
    assert last["type"] == "failed"
    assert last["reason"] == "stalled"
    assert last["last_event_at"].endswith("Z")
    assert record["last_event_at"] == last["last_event_at"]


def test_a_run_that_keeps_talking_past_its_wall_clock_limit_is_timed_out(tmp_path: Path) -> None:
    """Events alone do not keep an attempt alive forever: the wall clock bounds it too."""
    limits = LaneLimits(1.0, 30.0, 5.0, 0.05, 1.0)
    lane, attempts = runner(
        tmp_path,
        "while True:\n    event('text_delta', text='.')\n    time.sleep(0.05)\n",
        limits=limits,
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "timeout"
    last = events_of(lane, record["run_id"])[-1]
    assert (last["type"], last["reason"]) == ("failed", "timeout")


def test_a_run_that_never_wrote_an_event_still_gets_its_outcome_recorded(tmp_path: Path) -> None:
    """A run that hung before its first event (server start, the first model call) has no
    events file yet. Its outcome is recorded anyway, so no run id is left without one."""
    lane, attempts = runner(tmp_path, "EVENTS.unlink(missing_ok=True)\ntime.sleep(600)\n")
    record = attempts.run(1, "plan")
    assert record["status"] == "stalled"
    assert record["last_event_at"] is None
    (only,) = events_of(lane, record["run_id"])
    assert (only["type"], only["reason"]) == ("failed", "stalled")


def test_a_run_that_already_ended_is_not_given_a_second_verdict(tmp_path: Path) -> None:
    lane, attempts = runner(
        tmp_path,
        """
        event('failed', reason='turn limit or empty response')
        verdict(status='failed', turns=60)
        """,
        limits=PATIENT,
    )
    record = attempts.run(1, "plan")
    assert [e["reason"] for e in events_of(lane, record["run_id"])] == [
        "turn limit or empty response"
    ]


def test_an_attempt_that_dies_without_a_verdict_is_recorded_as_crashed(tmp_path: Path) -> None:
    lane, attempts = runner(
        tmp_path, "event('turn.completed', turn=1)\nsys.exit(3)\n", limits=PATIENT
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "crashed"
    assert events_of(lane, record["run_id"])[-1]["reason"] == "crashed"


def test_an_unavailable_model_is_recorded_as_the_run_outcome(tmp_path: Path) -> None:
    lane, attempts = runner(
        tmp_path,
        "verdict(status='unavailable', error='timed out')\n",
        limits=PATIENT,
    )
    record = attempts.run(1, "plan")
    assert (record["status"], record["error"]) == ("unavailable", "timed out")
    assert events_of(lane, record["run_id"])[-1]["reason"] == "unavailable"


def test_a_signalled_lane_stops_its_attempt_instead_of_orphaning_it(tmp_path: Path) -> None:
    """storm-stop.py SIGTERMs the lane. The attempt lives in a session of its own, so the
    default disposition -- the lane dying on the spot -- would leave it running unwatched."""
    import signal
    import threading

    marker = tmp_path / "child.pid"
    lane, attempts = runner(
        tmp_path,
        f"Path({str(marker)!r}).write_text(str(os.getpid()))\ntime.sleep(600)\n",
        limits=PATIENT,
    )

    def stop_when_started() -> None:
        deadline = time.monotonic() + 20
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        os.kill(os.getpid(), signal.SIGTERM)

    before = signal.getsignal(signal.SIGTERM)
    threading.Thread(target=stop_when_started, daemon=True).start()
    record = attempts.run(1, "plan")
    assert record["status"] == "stopped"
    assert gone(int(marker.read_text()))
    assert events_of(lane, record["run_id"])[-1]["reason"] == "stopped"
    (line,) = (tmp_path / "progress.log").read_text().splitlines()
    assert " stopped a-lane #504: attempt 1/3 was interrupted by a signal" in line
    assert signal.getsignal(signal.SIGTERM) == before  # the previous disposition is back


def test_a_pid_planted_in_the_lane_is_never_signalled(tmp_path: Path) -> None:
    """The lane tree is the model's to write -- its shell tool runs any command there. A pid
    planted anywhere in it must not reach `killpg`: only what the attempt reports over its
    private channel is recorded, so a same-user process outside the attempt survives."""
    victim = subprocess.Popen(["sleep", "600"], start_new_session=True)
    try:
        lane, attempts = runner(
            tmp_path,
            f"""
            for where in [Path('.qwenstorm/attempts/1.pids'), Path('pids'), EVENTS.parent / 'pids']:
                where.parent.mkdir(parents=True, exist_ok=True)
                where.write_text('{victim.pid}\\n')
            time.sleep(600)
            """,
        )
        record = attempts.run(1, "plan")
        assert record["status"] == "stalled"
        assert victim.poll() is None, "a pid planted in the lane was signalled"
    finally:
        victim.kill()
        victim.wait()


def test_a_reported_pid_is_signalled_only_while_it_is_an_attempt_session() -> None:
    """Even over the private channel, nothing outside what an attempt can have started is
    signalled: not init, not a non-positive pid, not this process or its own group, not a
    process that leads no session of its own, and not a group that no longer exists."""
    watchdog = lane_watchdog.AttemptWatchdog(FAST)
    for refused in (-1, 0, 1, os.getpid(), os.getpgrp()):
        assert not watchdog.signallable(refused), refused
    same_session = subprocess.Popen(["sleep", "600"])
    own_session = subprocess.Popen(["sleep", "600"], start_new_session=True)
    try:
        assert not watchdog.signallable(same_session.pid)
        assert watchdog.signallable(own_session.pid)
    finally:
        for process in (same_session, own_session):
            process.kill()
            process.wait()
    assert not watchdog.signallable(own_session.pid)


def test_a_crashed_attempt_leaves_no_tool_running_into_the_next_one(tmp_path: Path) -> None:
    """An attempt that dies without a verdict (a crash, an OOM kill) never reaches the
    watchdog's stop, and the commands it started in sessions of their own would keep
    changing the lane while the next attempt starts. They are stopped before any retry."""
    marker = tmp_path / "tool.pid"
    _, attempts = runner(
        tmp_path,
        f"""
        tool = subprocess.Popen(['sleep', '600'], start_new_session=True)
        record(tool.pid)
        Path({str(marker)!r}).write_text(str(tool.pid))
        os._exit(9)
        """,
        limits=PATIENT,
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "crashed"
    assert gone(int(marker.read_text())), "a crashed attempt's tool outlived it"


def test_touching_the_events_file_is_not_progress(tmp_path: Path) -> None:
    """Only appended bytes are liveness. A stalled attempt -- or a command the model left
    running -- that merely touches events.jsonl must not reset the stall clock."""
    _, attempts = runner(
        tmp_path,
        """
        event('turn.completed', turn=1)
        while True:
            os.utime(EVENTS)
            time.sleep(0.05)
        """,
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "stalled"


def test_every_class_honours_the_interface_declared_beside_it(tmp_path: Path) -> None:
    """ADR-0016 / 9.b: each class has a Protocol beside it, and each conforms to it."""
    declared = _load("lane_watchdog_interface", "interfaces/lane_watchdog_interface.py")
    limits = LaneLimits.declared(tmp_path)
    outcome = lane_watchdog.AttemptOutcome("exited", 0, 1.0, 0.5, None, None)
    attempts = lane_watchdog.LaneAttempts(
        tmp_path,
        slug="s",
        issue=1,
        max_attempts=1,
        limits=limits,
        progress_log=tmp_path / "progress.log",
        state_dir=tmp_path / "state",
        child_argv=lambda spec: [],
    )
    read_end, write_end = os.pipe()
    try:
        guard = lane_watchdog.ChildGuard(write_end)
        pairs = [
            (limits, declared.LaneLimitsInterface),
            (outcome, declared.AttemptOutcomeInterface),
            (lane_watchdog.AttemptWatchdog(limits), declared.AttemptWatchdogInterface),
            (attempts, declared.LaneAttemptsInterface),
            (guard, declared.ChildGuardInterface),
        ]
        for instance, interface in pairs:
            assert isinstance(instance, interface), interface.__name__
    finally:
        os.close(read_end)
        os.close(write_end)


# --- progress.log says it in words -----------------------------------------------------------


def test_a_stall_is_reported_in_progress_log_in_words(tmp_path: Path) -> None:
    _, attempts = runner(tmp_path, "event('turn.completed', turn=1)\ntime.sleep(600)\n")
    attempts.run(2, "plan")
    (line,) = (tmp_path / "progress.log").read_text().splitlines()
    assert " stalled a-lane #504: attempt 2/3 wrote no event for " in line
    assert "last event at " in line
    assert "process tree was stopped" in line
    assert "counts as a failed attempt" in line
    # storm-watch counts " end " lines as finished lanes; this line must not be one.
    assert " end " not in line


def test_a_timeout_is_reported_in_progress_log_in_words(tmp_path: Path) -> None:
    limits = LaneLimits(1.0, 30.0, 5.0, 0.05, 1.0)
    _, attempts = runner(
        tmp_path, "while True:\n    event('x')\n    time.sleep(0.05)\n", limits=limits
    )
    attempts.run(1, "plan")
    (line,) = (tmp_path / "progress.log").read_text().splitlines()
    assert (
        " timed out a-lane #504: attempt 1/3 ran past its 1s per-attempt wall-clock limit" in line
    )


# --- the lane budget -------------------------------------------------------------------------


def test_the_lane_limit_bounds_the_attempt_and_then_the_lane(tmp_path: Path) -> None:
    """The lane's own wall clock caps each attempt at what is left of it, and once it is spent
    no further attempt starts -- reported in words, since no attempt is there to report it."""
    limits = LaneLimits(30.0, 1.0, 30.0, 0.05, 1.0)
    _, attempts = runner(
        tmp_path, "while True:\n    event('x')\n    time.sleep(0.05)\n", limits=limits
    )
    first = attempts.run(1, "plan")
    assert first["status"] == "timeout"
    assert attempts.run(2, "plan") is None
    first_line, second_line = (tmp_path / "progress.log").read_text().splitlines()
    assert "per-lane wall-clock limit" in first_line
    assert "no further attempt was started" in second_line
    assert "attempt 2/3" in second_line


# --- qwenlane: a killed attempt is a failed attempt ------------------------------------------


@pytest.fixture
def qwenlane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # noqa: ANN201 - a module
    monkeypatch.setenv("QWENLOOP_CONFIG", str(TOOLS.parent / "qwen-storm.toml"))
    module = _load("qwenlane", "qwenlane.py")
    monkeypatch.setattr(module, "STORM", tmp_path)
    return module


def git_lane(tmp_path: Path) -> Path:
    lane = tmp_path / "lanes" / "a-lane"
    lane.mkdir(parents=True)
    run = {"cwd": lane, "check": True, "capture_output": True}
    subprocess.run(["git", "init", "-q"], **run)
    (lane / "README.md").write_text("a lane\n")
    subprocess.run(["git", "add", "README.md"], **run)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], **run
    )
    return lane


def test_qwenlane_counts_every_stalled_attempt_against_max_attempts(
    tmp_path: Path, qwenlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = git_lane(tmp_path)
    (tmp_path / "storm.toml").write_text(
        "[lane]\nstall_timeout_seconds = 1\nwatchdog_poll_seconds = 0.05\nkill_grace_seconds = 1\n"
    )
    body = tmp_path / "issue.md"
    body.write_text("fix it\n")
    # The lane runs only text the admission seam vouched for (storm_trust, 12.j): the
    # record binds this exact title and these exact bytes, as `IssueGate.admit` writes it.
    (lane / ".qwenstorm").mkdir(exist_ok=True)
    (lane / ".qwenstorm" / "provenance.json").write_text(
        json.dumps(
            {
                "issue": 504,
                "admitted": True,
                "title": "a title",
                "author": "operator",
                "source": "owner/repo#504",
                "fetched_at": "2026-09-23T00:00:00Z",
                "sha256": qwenlane.Admission().digest("a title", body.read_bytes()),
            }
        )
    )
    argv = child(tmp_path, "event('turn.completed', turn=1)\ntime.sleep(600)\n")
    monkeypatch.setattr(qwenlane, "attempt_argv", lambda spec: [*argv, str(spec)])
    monkeypatch.setattr(
        sys, "argv", ["qwenlane.py", str(lane), "504", "a title", str(body), "--max-attempts", "2"]
    )
    # A lane starts only with an environment of its own (lane_environment.py), which main()
    # enters by rewriting os.environ -- so it is given one, and os.environ is restored after.
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(lane / ".venv")],
        check=True,
        capture_output=True,
    )
    plain = {"HOME": os.environ.get("HOME", "/"), "PATH": os.pathsep.join(["/usr/bin", "/bin"])}
    with mock.patch.dict(os.environ, plain, clear=True):
        qwenlane.main()
    result = json.loads((lane / ".qwenstorm" / "result.json").read_text())
    assert result["completed"] is False
    assert [a["status"] for a in result["attempts"]] == ["stalled", "stalled"]
    assert len((tmp_path / "progress.log").read_text().splitlines()) == 2


def test_the_attempt_child_runs_the_plan_and_records_escaping_pids(
    tmp_path: Path, qwenlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The child half: it runs one qwenloop plan, writes the verdict for the parent, and
    records every subprocess started in a session of its own so the parent can reach it."""
    import asyncio

    lane = tmp_path / "lane"
    (lane / ".qwenstorm").mkdir(parents=True)
    seen: dict[str, object] = {}

    class State:
        status = qwenlane.RunStatus.COMPLETED
        turns = 4

    async def fake_run_plan(server, profile, cwd, run_id, text, max_turns, **kwargs):  # noqa: ANN001, ANN202
        process = await asyncio.create_subprocess_exec("true", start_new_session=True)
        await process.wait()
        seen.update(cwd=cwd, run_id=run_id, text=text, pid=process.pid)
        return State()

    monkeypatch.setattr(qwenlane, "_run_plan", fake_run_plan)
    monkeypatch.setattr(qwenlane, "_server_for", lambda config: (None, None))
    read_end, write_end = os.pipe()
    monkeypatch.setenv(lane_watchdog.REPORT_FD_ENV, str(write_end))
    spec = write_spec(tmp_path, lane, monkeypatch)
    original = asyncio.create_subprocess_exec
    try:
        assert qwenlane.run_attempt(spec) == 0
    finally:
        asyncio.create_subprocess_exec = original
    os.close(write_end)
    with os.fdopen(read_end) as stream:
        lines = stream.read().splitlines()
    assert lines == [f"pid {seen['pid']}", 'result {"status": "completed", "turns": 4}']
    assert (seen["cwd"], seen["run_id"], seen["text"]) == (lane, "run-1", "the plan")
    # The channel is the child's alone: nothing it started in a new session inherits it,
    # and nothing about it is left in the environment those commands see.
    assert lane_watchdog.REPORT_FD_ENV not in os.environ
    assert lane_watchdog.SPEC_SHA256_ENV not in os.environ
    assert not list(lane.rglob("*.pids"))


def write_spec(tmp_path: Path, lane: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A spec as the parent writes it, with its digest handed over out of band."""
    import hashlib

    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "lane": str(lane),
                "run_id": "run-1",
                "plan": "the plan",
                "events": str(lane / ".qwenloop/runs/run-1/events.jsonl"),
                "poll_seconds": 60,
            }
        )
    )
    monkeypatch.setenv(lane_watchdog.SPEC_SHA256_ENV, hashlib.sha256(spec.read_bytes()).hexdigest())
    return spec


def test_a_spec_rewritten_after_the_parent_wrote_it_is_refused(
    tmp_path: Path, qwenlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The spec carries the plan the child runs. A process that escaped an earlier attempt
    could rewrite it between the parent's write and the child's read; the child checks the
    bytes against the digest the parent handed it out of band, and runs nothing on a
    mismatch."""
    lane = tmp_path / "lane"
    lane.mkdir()
    ran: list[object] = []

    async def fake_run_plan(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        ran.append(args)

    monkeypatch.setattr(qwenlane, "_run_plan", fake_run_plan)
    monkeypatch.setattr(qwenlane, "_server_for", lambda config: (None, None))
    read_end, write_end = os.pipe()
    monkeypatch.setenv(lane_watchdog.REPORT_FD_ENV, str(write_end))
    spec = write_spec(tmp_path, lane, monkeypatch)
    spec.write_text(spec.read_text().replace("the plan", "rm the world"))
    assert qwenlane.run_attempt(spec) != 0
    os.close(write_end)
    with os.fdopen(read_end) as stream:
        (line,) = stream.read().splitlines()
    kind, _, verdict = line.partition(" ")
    assert kind == "result"
    found = json.loads(verdict)
    assert found["status"] == "crashed"
    assert "does not match" in found["error"]
    assert ran == []
    assert lane_watchdog.SPEC_SHA256_ENV not in os.environ


def test_a_spec_with_no_digest_is_refused(
    tmp_path: Path, qwenlane, monkeypatch: pytest.MonkeyPatch
) -> None:
    lane = tmp_path / "lane"
    lane.mkdir()
    read_end, write_end = os.pipe()
    monkeypatch.setenv(lane_watchdog.REPORT_FD_ENV, str(write_end))
    spec = write_spec(tmp_path, lane, monkeypatch)
    monkeypatch.delenv(lane_watchdog.SPEC_SHA256_ENV)
    assert qwenlane.run_attempt(spec) != 0
    os.close(write_end)
    with os.fdopen(read_end) as stream:
        assert '"status": "crashed"' in stream.read()


def test_the_spec_is_written_outside_the_lane_and_bound_end_to_end(tmp_path: Path) -> None:
    """Through the real `qwenlane.py --attempt`: the spec lives in the storm's state dir, not
    the lane's worktree, and one rewritten after the parent wrote it is refused before
    qwenloop runs -- the attempt ends `crashed`, saying why."""
    lane = tmp_path / "lanes" / "a-lane"
    lane.mkdir(parents=True)
    written: list[Path] = []

    def tamper_then_start(spec: Path) -> list[str]:
        written.append(spec)
        spec.write_text(spec.read_text().replace('"plan"', '"plan", "x": 1, "_"', 1))
        return [sys.executable, str(TOOLS / "qwenlane.py"), "--attempt", str(spec)]

    attempts = lane_watchdog.LaneAttempts(
        lane,
        slug="a-lane",
        issue=504,
        max_attempts=1,
        limits=PATIENT,
        progress_log=tmp_path / "progress.log",
        state_dir=tmp_path / "state",
        child_argv=tamper_then_start,
    )
    record = attempts.run(1, "plan")
    assert record["status"] == "crashed"
    assert "does not match" in record["error"]
    (spec,) = written
    assert spec.is_relative_to(tmp_path / "state")
    assert not spec.is_relative_to(lane)
    assert not (lane / ".qwenstorm" / "attempts").exists()


# --- a repository checkout never commits a storm's runtime -----------------------------------

PLANS = TOOLS.parent
REPO = PLANS.parents[2]


def ignored(path: Path) -> bool:
    """Whether git's ignore rules match `path` in this checkout. It need not exist.

    `--no-index`: judged by the rules alone, so a tracked ledger an over-broad pattern would
    hide still reads as ignored here, rather than passing because it is already tracked.
    """
    done = subprocess.run(
        ["git", "check-ignore", "-q", "--no-index", str(path.relative_to(REPO))],
        cwd=REPO,
        capture_output=True,
    )
    assert done.returncode in (0, 1), done.stderr
    return done.returncode == 0


@pytest.mark.parametrize(
    "runtime",
    [
        "lanes/a-lane/README.md",
        "lanes/a-lane/.qwenstorm/result.json",
        "lanes/a-lane/.git/HEAD",
        "state/attempts/a-lane/1.json",
    ],
)
def test_the_storm_runtime_is_never_tracked_from_a_checkout(runtime: str) -> None:
    """Run from a repository checkout, `storm_paths.storm()` is this plans directory, so the
    lane clones and the attempt specs land in it. Neither may ever be swept into a commit."""
    assert ignored(PLANS / runtime), runtime


@pytest.mark.parametrize(
    "ledger",
    [
        "integrated.txt",
        "abandoned.txt",
        "queue.txt",
        "evidence/ledger.jsonl",
        "evidence/CHANGES.md",
        "lanes/.gitignore",
        "state/.gitignore",
    ],
)
def test_the_ledgers_and_the_ignore_files_stay_tracked(ledger: str) -> None:
    assert not ignored(PLANS / ledger), ledger
