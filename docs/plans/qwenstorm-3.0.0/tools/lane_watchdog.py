"""A lane cannot hang the storm: wall-clock limits and a stall watchdog for qwenlane attempts.

Lanes run strictly one at a time -- one model slot, one loop instance (8.c) -- and
`storm-queue.sh` starts nothing while a `qwenlane.py` is alive. So one attempt that never
returns stops the whole storm, and until this existed nothing bounded one. On 2026-09-23 a
run wrote its last event at 09:17:39Z and the storm sat idle until a human restarted it at
10:50Z: 93 minutes, with no terminal event, so every downstream tool still reads that run's
outcome as unknown. Four runs on disk end that way.

WHAT THIS DOES
--------------
Each attempt runs in a process of its own, in a session of its own, and is watched from
outside. Three limits end it:

  * the per-attempt wall clock;
  * the per-lane wall clock, which caps every attempt at what is left of it and, once
    spent, starts no further attempt;
  * the stall watchdog: a run whose `events.jsonl` has not grown for the stall limit is
    stalled, however alive its process looks.

On any of them the attempt's whole process tree is stopped (SIGTERM, a grace period, then
SIGKILL), a terminal event is appended to the run's `events.jsonl` saying why and when the
last event was, the attempt counts as a failed attempt under `--max-attempts`, and
`progress.log` says so in words.

WHY A CHILD PROCESS, AND WHY THE PID FILE
-----------------------------------------
qwenlane used to run qwenloop in-process. That cannot be bounded from inside: a model call
blocks in `urllib` on a worker thread (`asyncio.to_thread`), and a thread cannot be
cancelled. A separate process can always be killed.

Killing its process group is not the whole tree, though. qwenloop's shell tool starts every
command with `start_new_session=True`, so a hung `pytest` the model launched lives in a
session of its own and survives a `killpg` of the lane. The child reports the pid of every
subprocess it starts in a new session (`ChildGuard`), and because a session leader's pid is
its process group id, the watchdog reaches each of those groups by pid -- no `ps`, which the
storm's tools cannot rely on (see storm-stop.py).

WHERE THOSE PIDS TRAVEL, AND WHY NOT THROUGH A FILE
---------------------------------------------------
Not through the lane tree. The lane is the model's to write -- its shell tool runs any
command there -- so a registry in it would let a prompt plant any pid and have a timeout
`killpg` an unrelated process group of the same user. The child reports over a pipe the
parent creates and hands it by descriptor (`QWENLANE_REPORT_FD`); the descriptor is made
non-inheritable in the child, so no command it starts can write to it. The verdict travels
the same way, so nothing the lane can write decides how an attempt ended.

The attempt's spec -- which carries the plan the child runs -- is written under the storm's
state directory, outside the lane's worktree, and bound by digest: the parent hands the
child the sha256 of the exact bytes it wrote (`QWENLANE_SPEC_SHA256`), and a child that
reads anything else reports `crashed` and runs nothing.

Even so, every pid is checked before it is signalled (`AttemptWatchdog.signallable`): never
pid 1 or below, never this process or its own group, and only while it still leads a
session of its own -- or, once that leader has exited, while the group it left still
exists, since a process group id cannot be reused while its group does. Groups that vanish
are forgotten at the next poll. Descent is established by provenance: only the attempt
itself can write the channel, and it reports a pid the moment it created that process.

THE LIMITS ARE DECLARED
-----------------------
In `storm.toml`, section `[lane]` (12.h); an absent key falls back to the measured default
below, the way `lane-reap.py` falls back for `[issues] abandoned_label`:

    [lane]
    attempt_timeout_seconds = 2400
    lane_timeout_seconds = 5400
    stall_timeout_seconds = 1200
    watchdog_poll_seconds = 5
    kill_grace_seconds = 30

Underscored, not hyphenated, because this one is imported rather than run.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import math
import os
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import storm_paths

# --- The measured defaults ---------------------------------------------------------------
# Measured 2026-09-23 over every `lanes/*/.qwenloop/runs/*/events.jsonl` of the QwenStorm
# 3.0.0 run: 82 runs, 78 of them ending with a terminal event, 5,736 turns. Only
# `turn.completed` carries timestamps, so the gaps are bounded from above per turn: the
# silence before a turn's first event is (its start - the previous turn's end) + model_ms,
# and the silence inside its tool phase is at most duration_ms - model_ms.

#: Longest attempt that reached a verdict: 1,128 s (split-351-1-amqp-contract); p90 825 s,
#: p50 429 s. Twice the longest, rounded up to whole minutes: 40 minutes.
ATTEMPT_SECONDS = 2400
#: Longest lane that ended with a verdict, start to end in progress.log over 41 lanes:
#: 2,206 s (chart-operator-forgejo-p1, three attempts). About two and a half times that:
#: 90 minutes, which binds before three full-length attempts (3 x 2,400 s) would.
LANE_SECONDS = 5400
#: Longest healthy silence between two events: 215.5 s (a model call); p99 67.5 s; the tool
#: phase never exceeded its own 120 s cap. But a model call may legitimately stay silent
#: until qwenloop's own request timeout, `idle_timeout_seconds` = 900 s, and one shell tool
#: call (120 s) can follow it before the next event is written. Killing inside that window
#: would pre-empt qwenloop's clean `unavailable` with a kill, so the limit clears 1,020 s
#: with margin: 20 minutes, 5.6 times the longest silence ever observed.
STALL_SECONDS = 1200
#: How often the watchdog looks. Precision of every limit above, not a limit itself.
POLL_SECONDS = 5
#: How long a SIGTERMed tree gets to exit before SIGKILL.
GRACE_SECONDS = 30

#: Names the descriptor of the attempt's private report channel in the child's environment.
REPORT_FD_ENV = "QWENLANE_REPORT_FD"
#: Names the sha256 of the exact spec bytes the parent wrote, in the child's environment.
#: An environment variable rather than a second descriptor: the child's own environment is
#: fixed when the parent starts it and no other process can change it, the digest needs no
#: secrecy (only integrity), and the child pops it before any command runs, so it rides in
#: the same place as REPORT_FD_ENV with no second pipe to open, pass, drain and close.
SPEC_SHA256_ENV = "QWENLANE_SPEC_SHA256"

#: Event types that end a run in qwenloop's own vocabulary.
TERMINAL_EVENTS = frozenset({"completed", "failed"})


def _seconds(root: Path, key: str, default: float) -> float:
    """One `[lane]` limit from storm.toml: a positive number of seconds, or the default.

    Module-level for the reason `storm_paths` is: every class here and the tests read limits
    the same way, and there is no state to hang it on.
    """
    raw = storm_paths.declared(root, "lane", key)
    if raw is None:
        return float(default)
    try:
        # `declared` stringifies; a TOML boolean arrives as "True" and is refused here.
        value = float(raw)
    except ValueError:
        value = 0.0
    if not (math.isfinite(value) and value > 0):
        # Zero kills every attempt at once, a word would silently mean the default, and inf
        # (or nan, which compares false with everything) switches the limit off -- none is
        # what a safety limit may be declared as, so the lane refuses to start (10.f).
        raise SystemExit(
            f"{root / storm_paths.CONFIG}: [lane] {key} must be a positive number of "
            f"seconds, not {raw!r}"
        )
    return value


def _span(seconds: float) -> str:
    """A duration in words a person reads at a glance: 45s, 20m00s, 1h30m00s."""
    whole = int(round(seconds))
    if whole < 60:
        return f"{whole}s"
    minutes, secs = divmod(whole, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s"


def _stamp(moment: float | None = None) -> str:
    """UTC, ISO-8601, to the millisecond -- the form qwenloop's own timed events carry."""
    when = datetime.fromtimestamp(time.time() if moment is None else moment, UTC)
    return when.isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class LaneLimits:
    """Every limit the watchdog enforces, in seconds."""

    attempt_seconds: float
    lane_seconds: float
    stall_seconds: float
    poll_seconds: float
    grace_seconds: float

    @classmethod
    def declared(cls, root: Path) -> LaneLimits:
        """The limits `root/storm.toml` declares, each absent key at its measured default."""
        return cls(
            attempt_seconds=_seconds(root, "attempt_timeout_seconds", ATTEMPT_SECONDS),
            lane_seconds=_seconds(root, "lane_timeout_seconds", LANE_SECONDS),
            stall_seconds=_seconds(root, "stall_timeout_seconds", STALL_SECONDS),
            poll_seconds=_seconds(root, "watchdog_poll_seconds", POLL_SECONDS),
            grace_seconds=_seconds(root, "kill_grace_seconds", GRACE_SECONDS),
        )


@dataclass(frozen=True)
class AttemptOutcome:
    """How one watched attempt ended.

    `reason` is `exited` (the process ended by itself), `timeout`, `stalled`, or `stopped`
    (this lane was signalled). `silent_seconds` is how long the run had been quiet then.
    `verdict` is what the attempt reported over its private channel, if anything.
    """

    reason: str
    returncode: int | None
    elapsed_seconds: float
    silent_seconds: float
    last_event_at: str | None
    verdict: dict[str, Any] | None


class _Stopped(Exception):
    """Raised from the signal handler so the watch loop can clean up before exiting."""


class AttemptWatchdog:
    """Runs one attempt in a session of its own and ends it when a limit is crossed."""

    def __init__(self, limits: LaneLimits) -> None:
        self._limits = limits
        self._groups: set[int] = set()
        self._pending = b""
        self._verdict: dict[str, Any] | None = None

    def watch(
        self,
        argv: list[str],
        *,
        cwd: Path,
        events: Path,
        budget_seconds: float,
        extra_env: Mapping[str, str] | None = None,
    ) -> AttemptOutcome:
        self._groups, self._pending, self._verdict = set(), b"", None
        started = time.monotonic()
        quiet_since = started
        seen = self._mark(events)
        read_end, write_end = os.pipe()
        os.set_blocking(read_end, False)
        try:
            with self._stop_on_signal():
                # Started inside the handler's reach, so a SIGTERM from here on stops the tree.
                process = subprocess.Popen(  # nosec B603 - argv is built by qwenlane, not the lane
                    argv,
                    cwd=cwd,
                    start_new_session=True,
                    pass_fds=(write_end,),
                    env={**os.environ, **(extra_env or {}), REPORT_FD_ENV: str(write_end)},
                )
                os.close(write_end)
                write_end = -1
                try:
                    while True:
                        try:
                            returncode = process.wait(timeout=self._limits.poll_seconds)
                        except subprocess.TimeoutExpired:
                            returncode = None
                        now = time.monotonic()
                        self._drain(read_end)
                        self._forget_vanished()
                        mark = self._mark(events)
                        if mark != seen:
                            seen, quiet_since = mark, now
                        if returncode is not None:
                            reason = "exited"
                        elif now - started >= budget_seconds:
                            reason = "timeout"
                        elif now - quiet_since >= self._limits.stall_seconds:
                            reason = "stalled"
                        else:
                            continue
                        break
                except _Stopped:
                    reason, now = "stopped", time.monotonic()
                self._drain(read_end)
                # Always, not only on a limit: an attempt that crashed or was OOM-killed
                # never reached a stop, and the commands it started in sessions of their own
                # would go on changing the lane while the next attempt starts.
                self.terminate(process)
                returncode = process.returncode
        finally:
            os.close(read_end)
            if write_end >= 0:
                os.close(write_end)
        return AttemptOutcome(
            reason=reason,
            returncode=returncode,
            elapsed_seconds=now - started,
            silent_seconds=now - quiet_since,
            last_event_at=self.last_event_at(events),
            verdict=self._verdict,
        )

    def terminate(self, process: subprocess.Popen[bytes]) -> None:
        """Stop the attempt's group and every session it reported: SIGTERM, grace, SIGKILL.

        Only groups that pass `signallable` at the moment of signalling are touched, and it is
        asked again before SIGKILL, so a group that went away in the grace period -- whose id
        could then be reused -- is never signalled a second time.
        """
        groups = [process.pid, *sorted(self._groups)]
        targets = [group for group in groups if self.signallable(group)]
        for group in targets:
            self._signal(group, signal.SIGTERM)
        deadline = time.monotonic() + self._limits.grace_seconds
        while targets and time.monotonic() < deadline:
            process.poll()  # reap it, or its zombie keeps its group "alive" below
            if not any(self._group_exists(group) for group in targets):
                break
            time.sleep(min(0.05, self._limits.poll_seconds))
        for group in targets:
            if self.signallable(group):
                self._signal(group, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=self._limits.grace_seconds)

    def signallable(self, group: int) -> bool:
        """Whether `group` may be signalled as one of an attempt's own process groups."""
        if group <= 1 or group in {os.getpid(), os.getpgrp()}:
            return False
        try:
            # The leader is alive: it must still lead the session it was started in.
            return os.getsid(group) == group
        except ProcessLookupError:
            # The leader has exited; its group may outlive it, and while it does the id
            # cannot have been reused.
            return self._group_exists(group)
        except PermissionError:
            return False

    @staticmethod
    def last_event_at(events: Path) -> str | None:
        """When the run last wrote an event: the file's own mtime, not when we noticed."""
        try:
            stat = events.stat()
        except OSError:
            return None
        return _stamp(stat.st_mtime) if stat.st_size else None

    @staticmethod
    def _mark(events: Path) -> int | None:
        """How many bytes of events there are. None while the file does not exist.

        Size alone, never mtime: the liveness signal is an appended event, and a touch -- by
        a command the model left running, say -- must not reset the stall clock.
        """
        try:
            return events.stat().st_size
        except OSError:
            return None

    def _drain(self, fd: int) -> None:
        """Read whatever the attempt has reported since the last look."""
        while True:
            try:
                chunk = os.read(fd, 65536)
            except BlockingIOError:
                return
            if not chunk:
                return
            self._pending += chunk
            *lines, self._pending = self._pending.split(b"\n")
            for line in lines:
                self._take(line.decode("utf-8", errors="replace"))

    def _take(self, line: str) -> None:
        kind, _, rest = line.partition(" ")
        if kind == "pid" and rest.isdigit():
            pid = int(rest)
            if self.signallable(pid):
                self._groups.add(pid)
        elif kind == "result":
            with contextlib.suppress(ValueError):
                found = json.loads(rest)
                if isinstance(found, dict) and "status" in found:
                    self._verdict = found

    def _forget_vanished(self) -> None:
        self._groups = {group for group in self._groups if self._group_exists(group)}

    @staticmethod
    def _signal(group: int, sig: signal.Signals) -> None:
        # A group that has already gone is not an error: the point is that nothing of this
        # attempt is left running, and a missing group is exactly that.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(group, sig)

    @staticmethod
    def _group_exists(group: int) -> bool:
        try:
            os.killpg(group, 0)
        except (ProcessLookupError, PermissionError):
            # PermissionError: it exists, but it is not ours, so it is not the attempt's.
            return False
        return True

    @staticmethod
    @contextlib.contextmanager
    def _stop_on_signal() -> Iterator[None]:
        """While an attempt runs, SIGTERM/SIGINT/SIGHUP stop it rather than orphan it.

        The attempt runs in a session of its own, so the default disposition -- this process
        dying on the spot -- would leave it running unwatched. `storm-stop.py` SIGTERMs the
        lane and expects it to go; now it goes and takes its tree with it.
        """
        if threading.current_thread() is not threading.main_thread():
            yield
            return

        caught_already: list[int] = []

        def stop(signum: int, frame: object) -> None:
            # Only the first: a second SIGTERM while the tree is being stopped must not
            # abandon the stopping half-way.
            if not caught_already:
                caught_already.append(signum)
                raise _Stopped(signum)

        caught = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        previous = {sig: signal.signal(sig, stop) for sig in caught}
        try:
            yield
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


class LaneAttempts:
    """The attempts of one lane, under one lane-wide wall clock.

    Every attempt runs `child_argv(spec)` watched by `AttemptWatchdog`; whatever ends it, the
    run's `events.jsonl` ends with a terminal event, and a limit or a stop is reported in
    `progress_log` in words.
    """

    def __init__(
        self,
        lane: Path,
        *,
        slug: str,
        issue: int,
        max_attempts: int,
        limits: LaneLimits,
        progress_log: Path,
        state_dir: Path,
        child_argv: Callable[[Path], list[str]],
    ) -> None:
        self._lane = lane
        self._slug = slug
        self._issue = issue
        self._max = max_attempts
        self._limits = limits
        self._progress = progress_log
        self._state = state_dir
        self._child_argv = child_argv
        self._deadline = time.monotonic() + limits.lane_seconds

    def run(self, attempt: int, plan: str) -> dict[str, Any] | None:
        """One attempt, as a result.json attempt record; None once the lane's clock is spent."""
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            self._say(
                "timed out",
                f"the lane spent its {_span(self._limits.lane_seconds)} per-lane wall-clock "
                f"limit before attempt {attempt}/{self._max}; no further attempt was started",
            )
            return None
        run_id = str(uuid.uuid4())
        # The spec carries the plan the child runs, so it is written outside the lane's
        # worktree -- which the model writes -- and bound by digest as well (see run_attempt).
        state = self._state / self._slug
        state.mkdir(parents=True, exist_ok=True)
        events = self._lane / ".qwenloop" / "runs" / run_id / "events.jsonl"
        spec = state / f"{attempt}.json"
        body = (
            json.dumps(
                {
                    "lane": str(self._lane),
                    "run_id": run_id,
                    "plan": plan,
                    "events": str(events),
                    "parent_pid": os.getpid(),
                    "poll_seconds": self._limits.poll_seconds,
                },
                indent=2,
            )
        ).encode("utf-8")
        spec.write_bytes(body)
        digest = hashlib.sha256(body).hexdigest()
        by_lane = remaining < self._limits.attempt_seconds
        outcome = AttemptWatchdog(self._limits).watch(
            self._child_argv(spec),
            cwd=self._lane,
            events=events,
            budget_seconds=remaining if by_lane else self._limits.attempt_seconds,
            extra_env={SPEC_SHA256_ENV: digest},
        )
        record: dict[str, Any] = {"attempt": attempt, "run_id": run_id}
        if outcome.reason == "exited":
            verdict = outcome.verdict
            if verdict is None:
                record["status"] = "crashed"
                record["error"] = (
                    f"the attempt exited with code {outcome.returncode} and no verdict"
                )
            else:
                record.update(verdict)
        else:
            record["status"] = outcome.reason
            record["last_event_at"] = outcome.last_event_at
        record.setdefault("turns", self._turns(events))
        self._record_terminal(events, record, outcome)
        self._report(attempt, outcome, by_lane)
        return record

    @staticmethod
    def _read(events: Path) -> list[dict[str, Any]]:
        try:
            lines = events.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        found = []
        for line in lines:
            with contextlib.suppress(ValueError):
                value = json.loads(line)
                if isinstance(value, dict):
                    found.append(value)
        return found

    def _turns(self, events: Path) -> int:
        return sum(1 for event in self._read(events) if event.get("type") == "turn.completed")

    def _record_terminal(
        self, events: Path, record: dict[str, Any], outcome: AttemptOutcome
    ) -> None:
        """Append a terminal event unless the run already wrote its own.

        A run qwenloop ended says so itself; one it did not -- killed, stalled, stopped,
        crashed, or refused by the model endpoint -- would otherwise end on whatever it was
        doing, and read as "outcome unknown" to every tool downstream (10.f).
        """
        if any(event.get("type") in TERMINAL_EVENTS for event in self._read(events)):
            return
        event = {
            "type": "failed",
            "reason": record["status"],
            "detail": record.get("error") or self._detail(outcome),
            "last_event_at": outcome.last_event_at,
            "at": _stamp(),
            "recorded_by": "qwenlane watchdog",
        }
        events.parent.mkdir(parents=True, exist_ok=True)
        with events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, sort_keys=True) + "\n")

    def _detail(self, outcome: AttemptOutcome) -> str:
        return (
            f"{outcome.reason} after {_span(outcome.elapsed_seconds)}, "
            f"{_span(outcome.silent_seconds)} since the last event"
        )

    def _report(self, attempt: int, outcome: AttemptOutcome, by_lane: bool) -> None:
        where = f"attempt {attempt}/{self._max}"
        last = (
            f"last event at {outcome.last_event_at}"
            if outcome.last_event_at
            else "the run never wrote an event"
        )
        stopped = "its process tree was stopped and it counts as a failed attempt"
        if outcome.reason == "stalled":
            self._say(
                "stalled",
                f"{where} wrote no event for {_span(outcome.silent_seconds)} ({last}; stall "
                f"limit {_span(self._limits.stall_seconds)}); {stopped}",
            )
        elif outcome.reason == "timeout":
            limit = self._limits.lane_seconds if by_lane else self._limits.attempt_seconds
            kind = "per-lane" if by_lane else "per-attempt"
            self._say(
                "timed out",
                f"{where} ran past its {_span(limit)} {kind} wall-clock limit ({last}); {stopped}",
            )
        elif outcome.reason == "stopped":
            self._say(
                "stopped",
                f"{where} was interrupted by a signal ({last}); its process tree was "
                "stopped and the lane was left unfinished, to be run again",
            )

    def _say(self, verb: str, why: str) -> None:
        """One progress.log line, in the storm's `<stamp> <verb> <slug>: <why>` form."""
        stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        line = f"{stamp} {verb} {self._slug} #{self._issue}: {why}\n"
        with self._progress.open("a", encoding="utf-8") as log:
            log.write(line)
        print(line, end="", flush=True)


class ChildGuard:
    """The attempt child's half: report what escapes its group, and die with its parent.

    It writes to the private channel the parent handed it (see the module docstring), which
    it makes non-inheritable first, so no command the model runs can write to it.

    `record_escaping_subprocesses` wraps `asyncio.create_subprocess_exec` -- the call
    qwenloop's shell tool makes -- so every subprocess started in a new session has its pid
    reported the moment it exists. Only those: a subprocess in the child's own group is
    already reached by the group kill. `report` sends the attempt's verdict the same way.

    `die_with(parent_pid, poll_seconds)` covers the case the watchdog cannot: the lane itself killed with
    SIGKILL. The child is in a session of its own, so it would otherwise run on unwatched,
    and `storm-queue.sh` would wait on it for as long as it hung.
    """

    def __init__(self, fd: int) -> None:
        self._fd = fd
        self._started: list[int] = []
        os.set_inheritable(fd, False)

    def record_escaping_subprocesses(self) -> None:
        original = asyncio.create_subprocess_exec

        async def recording(*args: Any, **kwargs: Any) -> asyncio.subprocess.Process:
            process = await original(*args, **kwargs)
            if kwargs.get("start_new_session"):
                self._started.append(process.pid)
                self._send(f"pid {process.pid}")
            return process

        asyncio.create_subprocess_exec = recording  # type: ignore[assignment]

    def report(self, verdict: dict[str, Any]) -> None:
        self._send("result " + json.dumps(verdict))

    def die_with(self, parent_pid: int, poll_seconds: float) -> None:
        threading.Thread(target=self._watch, args=(parent_pid, poll_seconds), daemon=True).start()

    def _send(self, line: str) -> None:
        # A parent that has gone has nobody to tell; die_with deals with that case.
        with contextlib.suppress(OSError):
            os.write(self._fd, (line + "\n").encode("utf-8"))

    def _watch(self, parent_pid: int, poll_seconds: float) -> None:
        while os.getppid() == parent_pid:
            time.sleep(poll_seconds)
        for group in self._started:
            with contextlib.suppress(OSError):
                if group > 1 and os.getsid(group) == group:
                    AttemptWatchdog._signal(group, signal.SIGTERM)
        if os.getpgrp() == os.getpid():  # only ever our own session's group
            AttemptWatchdog._signal(os.getpid(), signal.SIGTERM)
        os._exit(1)
