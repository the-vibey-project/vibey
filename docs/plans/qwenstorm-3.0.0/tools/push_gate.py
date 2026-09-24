"""The push gate: one pre-push gate run at a time, and a hung one reaped by rule, not by hand.

    python3 push_gate.py status                     # who holds the lock, and what it is doing
    python3 push_gate.py run -- git push origin HEAD:feat/x   # wait, push, always release
    token=$(python3 push_gate.py acquire --wait)    # the shell form: take the lock...
    python3 push_gate.py release "$token"           # ...and give it back (only its owner can)
    python3 push_gate.py reap --dry-run             # what it would do; signal, release, log nothing
    python3 push_gate.py reap                       # one reaper pass
    python3 push_gate.py install-schedule           # its own launchd/systemd schedule
    python3 push_gate.py schedule-status            # ...installed? loaded? how often?
    python3 push_gate.py uninstall-schedule

Parallel lanes push through one shared lock so that only one pre-push gate run -- the
import contract, the whole suite with its per-layer 100% coverage floors, bandit and
pip-audit -- happens at a time. The lock used to be a bare `mkdir`/`rmdir`. On 2026-09-24 one
push's pytest (8 xdist workers) sat at 0% CPU for 39 minutes, every worker asleep, while it
held that lock; every other push queued behind it until a human killed it. Nothing recorded
which test hung. This file is the lock as code, and the reaper that makes that night
impossible to repeat.

THE LOCK
--------
Still an atomic `mkdir`, so a caller of the old recipe and a caller of this one exclude each
other. Inside it, `owner.json` records who holds it: the holder's pid, the process group the
push runs in, the branch, the worktree, the start time, the uid, the command, and where the
push's output is being logged. `release` removes the lock only for the token that took it, and
only for the uid that took it. The lock path is declared (`[push_gate] lock` in storm.toml,
or `--lock`), never typed into the tool (12.c, 12.h); absent, it is `.push-lock` in the storm
home (`VIBEY_STORM_HOME`, else `[paths] home`, else ~/git/vibey-storm: storm_durability.py),
which is where the storm and every lane worktree live, on storage a reboot keeps (10.h).

`run` is the form to use. It starts the push in a session of its own, so the push and
everything it starts -- git, the hook, pre-commit, pytest, the xdist workers -- are one
process group that belongs to this push and to nothing else. That is what makes a kill safe.
It tees the push's output to a log the reaper can quote, and it releases the lock however
the push ends, including on SIGTERM, SIGINT and SIGHUP. `acquire` exists for the shell recipe
and records the shell's group, which may hold anything; a push taken that way is never killed
by the reaper, only released once its holder is gone.

THE REAPER: AUTOMATIC, BOUNDED BY A GATE (12.d, 12.e)
-----------------------------------------------------
Nobody should have to notice a hung push, so the reaper runs on a schedule of its own --
`install-schedule` renders the tracked templates in `templates/` into a launchd agent or a
systemd user timer, every `schedule_seconds` -- and also first in every `storm-cycle.py`
pass, and by hand. Hangs happen whenever anyone pushes, not only while a storm runs. A
non-blocking reap lock makes overlapping passes safe: the second stands aside, and every
action is keyed to the token or mtime it judged, so a later pass finds nothing left to do.
It acts only when one measured condition holds:

  (a) stale    the holder is gone, and so is the push's own group. The lock is released;
               nothing is killed, because nothing is left to kill. A dead holder whose push
               is still running is NOT stale: releasing would start a second gate run beside
               the first.
  (b) idle     the push's own group used less than `idle_cpu_seconds` of CPU in total over
               at least `idle_window_seconds`, measured from `ps -o time` samples taken
               pass by pass and kept on disk, so a hang is established over time and never
               from one snapshot. Any process appearing or vanishing in the window is
               activity, not idleness. An unreadable process table (the sandbox refuses
               `ps`) is UNKNOWN and never idle (10.f).
  (c) ceiling  the push has held the lock for `wall_ceiling_seconds`, busy or not.

A BARE `mkdir` LOCK (the old recipe, and the lock that hung on 2026-09-24) has no owner
record. `OwnerlessHolder` traces it by process: exactly one `git push` started within
`ownerless_match_seconds` of the lock's mtime, standing in (or `-C`'d at) a declared
`worktree_roots` entry, whose group holds only that push, its descendants and the shells
above it. That push is judged by the same idle and ceiling rules, and on a reap the lock is
removed if it is still the bare lock judged. Short of that, the answer is UNKNOWN and
nothing is killed.

Judgement is not one of them. Before a kill it refuses, and says why, when the push does not
run in a group of its own, when any member matches a `protected` pattern (Ollama, the review
runner), or when the group id no longer leads its own session (it may have been reused).

WHAT A REAP DOES, IN ORDER
--------------------------
1. Evidence, into `<state_dir>/evidence/<stamp>-<token>/`: the owner record, the decision
   and its measurements, the group's process tree, the last lines of the push log, and every
   pytest process's stacks -- `py-spy dump` when it is installed, else SIGUSR1, which the
   repository's tests/conftest.py registers with faulthandler to write one file per process
   under `VIBEY_PYTEST_STACKS_DIR` (which `run` sets).
2. The verdict for the pushing lane, `<state_dir>/verdicts/<token>.json`. `run` reads it
   when its push dies and reports `reaped: hang (...)` with exit 124 -- a hang, never a test
   failure. `release` reports the same to the shell recipe.
3. The kill: SIGTERM to the owner's process group, the declared grace, then SIGKILL. Only that
   group; never a process outside it.
4. The lock is removed, if and only if it still carries the token that was judged.
5. One JSON line appended to the reap log (`<state_dir>/reaps.jsonl`): time, owner, branch,
   condition, measurements, evidence path. Append-only; nothing is rewritten.

THE THRESHOLDS ARE DECLARED
---------------------------
In storm.toml, section `[push_gate]`; an absent key is the default below.

    [push_gate]
    lock = "../.push-lock"          # relative paths are read from the storm root;
    state_dir = "../.push-lock.gate"  # absent, both are in the storm home
    idle_cpu_seconds = 2
    idle_window_seconds = 600
    wall_ceiling_seconds = 3600
    kill_grace_seconds = 30
    poll_seconds = 20
    log_tail_lines = 200
    stack_wait_seconds = 3
    protected = ["ollama", "vibey-runner", "Runner.Listener", "Runner.Worker"]
    ownerless_match_seconds = 5
    worktree_roots = [".."]         # where a bare-mkdir push may stand; default: the lock's dir
    schedule_seconds = 90
    schedule_label = "org.vibey.push-gate-reaper"

A copy of this tool outside a storm root (the tracked one, in a checkout) has no storm.toml to
ask, so it takes the lock from `--lock` or `VIBEY_PUSH_LOCK`, and refuses without one.

Exit codes. `run`: the push's own, 124 when reaped, 125 past `--push-timeout`, 3 when
`--no-wait` or `--wait-timeout` gave up on the lock, 128+N when signalled. `reap`: 0 nothing to do, 1 reaped (or would have, under --dry-run), 2 a
person should look (unknown, or refused). `release`: 0 released, 1 not the owner, 124 reaped.

Underscored, not hyphenated: the tests import it.
"""

from __future__ import annotations

import argparse
import contextlib
import dataclasses
import fcntl
import json
import math
import os
import re
import shutil
import signal
import string
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import storm_durability
import storm_paths

# --- The declared defaults ---------------------------------------------------------------

#: CPU the push's whole group may use over the window and still be judged hung. A working
#: pre-push gate runs 8 xdist workers flat out (several CPU-s every wall second); the frozen
#: run of 2026-09-24 showed 0%. Two CPU-s in ten minutes is 0.3% of one core: far below any
#: suite doing work, and above `ps` rounding plus the housekeeping of sleeping workers.
IDLE_CPU_SECONDS = 2.0
#: The window idleness is measured over. Ten minutes: no honest test in either suite runs
#: near that long without burning CPU (tests/meta/test_a_hung_test_names_itself.py limits one
#: test to five), and it matches the storm cycle's ten-minute cadence, so two passes decide.
IDLE_WINDOW_SECONDS = 600.0
#: The hard ceiling on holding the lock, busy or not. The whole pre-push gate takes a few
#: minutes (the suite measured 147 s); an hour is more than ten of those.
WALL_CEILING_SECONDS = 3600.0
#: How long a SIGTERMed group gets to exit before SIGKILL.
GRACE_SECONDS = 30.0
#: How often a waiting `run` or `acquire --wait` looks at the lock again.
POLL_SECONDS = 20.0
#: How much of the push log goes into the evidence.
LOG_TAIL_LINES = 200
#: How long the suite gets to write its stacks after SIGUSR1, before the kill.
STACK_WAIT_SECONDS = 3.0
#: Never killed, whatever group they turn up in: the local model and the review runner.
PROTECTED = ("ollama", "vibey-runner", "Runner.Listener", "Runner.Worker")
#: A bare-mkdir lock is traced to the `git push` that started within this many seconds of the
#: lock's mtime. The old recipe (`until mkdir L; do sleep 20; done; git push ...`) starts the
#: push in the same shell line, a second or less after it takes the lock; `ps -o lstart` has
#: one-second resolution, so five seconds is tight without being fragile.
OWNERLESS_MATCH_SECONDS = 5.0
#: How often the standalone schedule runs one reaper pass. Within the one-to-two minutes the
#: operator asked for; the idle window is ten minutes, so this bounds detection to about that.
SCHEDULE_SECONDS = 90.0
#: The launchd Label and the systemd unit name.
SCHEDULE_LABEL = "org.vibey.push-gate-reaper"
#: PATH for the scheduled pass: `ps`, `lsof`, `git`, and py-spy when Homebrew installed it.
SCHEDULE_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
#: Shells the legacy recipe runs in; the only ancestors a traced push's group may contain.
SHELLS = frozenset({"sh", "bash", "zsh", "dash", "ksh"})

OWNER_FILE = "owner.json"
#: `run` exits with this when the reaper ended its push: a hang, not a test failure.
REAPED_EXIT = 124
#: `run --no-wait` and `acquire` exit with this when somebody else holds the lock.
HELD_EXIT = 3
#: `run --push-timeout` exits with this when it ended a push that ran past its own limit.
PUSH_TIMEOUT_EXIT = 125
#: Where the suite writes its SIGUSR1 stack dumps (tests/conftest.py reads it).
STACKS_ENV = "VIBEY_PYTEST_STACKS_DIR"
#: The machine's shared push lock, for a copy of this tool that is not in a storm root.
LOCK_ENV = "VIBEY_PUSH_LOCK"
#: Held (non-blocking) for the whole of one reaper pass, so two passes never both act.
REAP_LOCK = "reap.lock"
#: Tokens become file names; anything else is refused rather than escaped.
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _section(root: Path) -> dict[str, Any]:
    """The `[push_gate]` table of `root/storm.toml`, or empty.

    Module-level for the reason `storm_paths` gives: one stateless reader, shared by the
    config and nothing else. `storm_paths.declared` stringifies, and this needs to tell a
    number from a word before it believes either.
    """
    path = root / storm_paths.CONFIG
    if not path.is_file():
        return {}
    try:
        found = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise SystemExit(f"{path} could not be read: {exc}") from exc
    section = found.get("push_gate", {})
    return section if isinstance(section, dict) else {}


def _positive(root: Path, section: dict[str, Any], key: str, default: float) -> float:
    """A declared threshold: a finite positive number, or the default when absent.

    Module-level with `_section`, for the same reason. A zero, a word, a boolean or an
    infinity would each switch a safety limit off or make it fire at once; the reaper
    refuses to run on one rather than guess (10.f).
    """
    raw = section.get(key)
    if raw is None:
        return float(default)
    value = float(raw) if isinstance(raw, int | float) and not isinstance(raw, bool) else 0.0
    if not (math.isfinite(value) and value > 0):
        raise SystemExit(
            f"{root / storm_paths.CONFIG}: [push_gate] {key} must be a positive number, not {raw!r}"
        )
    return value


def _path(root: Path, raw: object, default: Path) -> Path:
    """A declared path, read from the storm root when relative. Module-level with `_section`."""
    if raw is None:
        return default
    path = Path(str(raw)).expanduser()
    return path if path.is_absolute() else root / path


def _span(seconds: float) -> str:
    """A duration a person reads at a glance: 45s, 2m05s, 1h30m00s. Module-level: pure."""
    whole = max(0, int(round(seconds)))
    if whole < 60:
        return f"{whole}s"
    minutes, secs = divmod(whole, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s"


def _iso(moment: float) -> str:
    """UTC, ISO-8601, to the second. Module-level: pure."""
    return datetime.fromtimestamp(moment, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- Configuration and records -----------------------------------------------------------


@dataclass(frozen=True)
class PushGateConfig:
    """Where the lock and its records are, and every threshold the reaper acts on."""

    lock: Path
    state_dir: Path
    reap_log: Path
    idle_cpu_seconds: float = IDLE_CPU_SECONDS
    idle_window_seconds: float = IDLE_WINDOW_SECONDS
    wall_ceiling_seconds: float = WALL_CEILING_SECONDS
    grace_seconds: float = GRACE_SECONDS
    poll_seconds: float = POLL_SECONDS
    log_tail_lines: int = LOG_TAIL_LINES
    stack_wait_seconds: float = STACK_WAIT_SECONDS
    protected: tuple[str, ...] = PROTECTED
    ownerless_match_seconds: float = OWNERLESS_MATCH_SECONDS
    worktree_roots: tuple[Path, ...] = ()
    schedule_seconds: float = SCHEDULE_SECONDS
    schedule_label: str = SCHEDULE_LABEL
    schedule_path: str = SCHEDULE_PATH

    @classmethod
    def declared(cls, root: Path, lock: Path | None = None) -> PushGateConfig:
        """What `root/storm.toml` declares; `lock` (from `--lock`) outranks it for one run."""
        section = _section(root)
        # Absent a declaration, the machine's shared lock in the storm home (10.h, ADR-0057).
        home = storm_durability.StormHome(os.environ, root)
        lock_path = lock or _path(root, section.get("lock"), home.push_lock())
        state = _path(root, section.get("state_dir"), lock_path.parent / f"{lock_path.name}.gate")
        protected = section.get("protected", PROTECTED)
        if not isinstance(protected, list | tuple) or not all(
            isinstance(p, str) and p for p in protected
        ):
            raise SystemExit(f"[push_gate] protected must be a list of names, not {protected!r}")
        roots = section.get("worktree_roots", [str(lock_path.parent)])
        if not isinstance(roots, list) or not all(isinstance(r, str) and r for r in roots):
            raise SystemExit(f"[push_gate] worktree_roots must be a list of paths, not {roots!r}")
        label = section.get("schedule_label", SCHEDULE_LABEL)
        if not isinstance(label, str) or not TOKEN.match(label):
            raise SystemExit(f"[push_gate] schedule_label must be a plain name, not {label!r}")
        return cls(
            lock=lock_path,
            state_dir=state,
            reap_log=_path(root, section.get("reap_log"), state / "reaps.jsonl"),
            idle_cpu_seconds=_positive(root, section, "idle_cpu_seconds", IDLE_CPU_SECONDS),
            idle_window_seconds=_positive(
                root, section, "idle_window_seconds", IDLE_WINDOW_SECONDS
            ),
            wall_ceiling_seconds=_positive(
                root, section, "wall_ceiling_seconds", WALL_CEILING_SECONDS
            ),
            grace_seconds=_positive(root, section, "kill_grace_seconds", GRACE_SECONDS),
            poll_seconds=_positive(root, section, "poll_seconds", POLL_SECONDS),
            log_tail_lines=int(_positive(root, section, "log_tail_lines", LOG_TAIL_LINES)),
            stack_wait_seconds=_positive(root, section, "stack_wait_seconds", STACK_WAIT_SECONDS),
            protected=tuple(protected),
            ownerless_match_seconds=_positive(
                root, section, "ownerless_match_seconds", OWNERLESS_MATCH_SECONDS
            ),
            worktree_roots=tuple(_path(root, r, root) for r in roots),
            schedule_seconds=_positive(root, section, "schedule_seconds", SCHEDULE_SECONDS),
            schedule_label=label,
            schedule_path=str(section.get("schedule_path", SCHEDULE_PATH)),
        )


@dataclass(frozen=True)
class Owner:
    """Who holds the lock: the record written inside it.

    `pid` holds the lock (the `run` wrapper, or the shell that ran `acquire`). `pgid` is the
    group the push runs in; `dedicated` says whether that group was created for this push
    alone, which is the only kind the reaper will ever kill.
    """

    token: str
    pid: int
    pgid: int | None
    dedicated: bool
    uid: int
    branch: str
    worktree: str
    started_at: float
    command: list[str] = field(default_factory=list)
    log: str | None = None
    stacks: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {**dataclasses.asdict(self), "started": _iso(self.started_at)}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> Owner:
        names = {f.name for f in dataclasses.fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in names})


@dataclass(frozen=True)
class LockState:
    """`free`, `owned` (with its owner) or `ownerless` (a bare mkdir, or a record unreadable)."""

    kind: str
    owner: Owner | None = None
    age_seconds: float | None = None
    detail: str = ""
    made_at: float | None = None


@dataclass(frozen=True)
class Proc:
    """One row of the process table."""

    pid: int
    ppid: int
    pgid: int
    cpu_seconds: float
    command: str
    started_at: float | None = None


@dataclass(frozen=True)
class Decision:
    """What one reaper pass decided.

    `action`: none, unknown, refused, released, killed, would-release, would-kill.
    `condition`: stale, idle, ceiling, or None when no condition held.
    """

    action: str
    condition: str | None
    detail: str
    measurements: dict[str, Any]
    owner: Owner | None = None
    evidence: Path | None = None

    def line(self) -> str:
        who = f" {self.owner.branch} (pid {self.owner.pid})" if self.owner else ""
        why = f" [{self.condition}]" if self.condition else ""
        where = f" evidence: {self.evidence}" if self.evidence else ""
        return f"push-gate: {self.action}{why}{who}: {self.detail}{where}"


# --- The seams: time, the process table, signals -----------------------------------------


class Clock:
    """Wall-clock time. A seam so the tests can drive an hour in a millisecond."""

    def now(self) -> float:
        return time.time()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class ProcessTable:
    """Read-only questions about processes: alive, grouped, and their CPU time.

    Liveness asks the kernel (`kill 0`), which works everywhere. Membership and CPU time need
    `ps`, which the sandbox the storm's tools often run in refuses outright; then `members`
    returns None, and None means UNKNOWN to every caller -- never "no processes", and never
    "idle" (10.f; storm-watch.py tells how a monitor that confused the two was believed).
    """

    # `lstart` is five words in the C locale on both macOS and procps: "Wed Sep 24 07:26:12 2026".
    PS = ("ps", "-A", "-o", "pid=,ppid=,pgid=,lstart=,time=,command=")
    LISTING = ("ps", "-A", "-o", "pid,ppid,pgid,stat,time,etime,command")

    def alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True  # it exists; it is simply not ours to signal
        return True

    def group_alive(self, pgid: int) -> bool:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def members(self, pgid: int) -> list[Proc] | None:
        rows = self._rows()
        if rows is None:
            return None
        return [row for row in rows if row.pgid == pgid]

    def processes(self) -> list[Proc] | None:
        """Every process, with its start time; None when the table cannot be read."""
        return self._rows()

    def cwd(self, pid: int) -> str | None:
        """Where `pid` is standing: /proc on Linux, `lsof` on macOS; None when unknowable."""
        with contextlib.suppress(OSError):
            return os.readlink(f"/proc/{pid}/cwd")
        out = self._ps(("lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"))
        for line in (out or "").splitlines():
            if line.startswith("n/"):
                return line[1:]
        return None

    def listing(self) -> str | None:
        out = self._ps(self.LISTING)
        return out

    def session_leader(self, pgid: int) -> bool:
        """Whether `pgid` is still the group a push started in a session of its own.

        Its leader must still lead that session; once the leader has exited, the group it
        left may outlive it, and while any member remains the id cannot be reused.
        """
        try:
            return os.getsid(pgid) == pgid
        except ProcessLookupError:
            return self.group_alive(pgid)
        except PermissionError:
            return False

    @staticmethod
    def cpu_seconds(text: str) -> float:
        """`ps -o time` in either spelling: M:SS.ss (macOS) or [D-]HH:MM:SS (procps)."""
        days = 0.0
        if "-" in text:
            head, text = text.split("-", 1)
            days = float(head)
        total = 0.0
        for part in text.split(":"):
            total = total * 60 + float(part)
        return days * 86400 + total

    def _rows(self) -> list[Proc] | None:
        out = self._ps(self.PS)
        if not out:
            return None
        rows: list[Proc] = []
        for line in out.splitlines():
            parts = line.split(None, 9)
            if len(parts) < 9:
                continue
            try:
                started = time.mktime(time.strptime(" ".join(parts[4:8]), "%b %d %H:%M:%S %Y"))
                rows.append(
                    Proc(
                        pid=int(parts[0]),
                        ppid=int(parts[1]),
                        pgid=int(parts[2]),
                        cpu_seconds=self.cpu_seconds(parts[8]),
                        command=parts[9] if len(parts) > 9 else "",
                        started_at=started,
                    )
                )
            except ValueError:
                continue
        return rows or None

    @staticmethod
    def _ps(argv: tuple[str, ...]) -> str | None:
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, no shell
                list(argv),
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "LC_ALL": "C"},
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if done.returncode != 0 or not done.stdout.strip():
            return None
        return done.stdout


class Signaller:
    """The only thing here that sends a signal. A group that is already gone is not an error."""

    def send_group(self, pgid: int, sig: int) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(pgid, sig)

    def send_process(self, pid: int, sig: int) -> None:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, sig)


# --- The lock ---------------------------------------------------------------------------


class PushLock:
    """The shared push lock: an atomic mkdir with the owner's record inside it.

    Every change to it -- take, update, release, evict -- happens under a `flock` on a file
    beside the state, so a reaper deciding and an owner releasing can never interleave and
    remove somebody else's lock.
    """

    def __init__(self, config: PushGateConfig, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    @property
    def path(self) -> Path:
        return self._config.lock

    def acquire(self, owner: Owner) -> bool:
        with self._mutex():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.path.mkdir()
            except FileExistsError:
                return False
            self._write(owner)
            return True

    def update(self, owner: Owner) -> bool:
        with self._mutex():
            current = self._read().owner
            if current is None or current.token != owner.token:
                return False
            self._write(owner)
            return True

    def state(self) -> LockState:
        return self._read()

    def release(self, token: str, uid: int) -> str:
        """`released`, `not-owner`, or `free` (nothing was held)."""
        with self._mutex():
            state = self._read()
            if state.kind == "free":
                return "free"
            if state.owner is None or state.owner.token != token or state.owner.uid != uid:
                return "not-owner"
            self._remove()
            return "released"

    def evict(self, token: str) -> bool:
        """The reaper's release: only if the lock still carries the token it judged."""
        with self._mutex():
            state = self._read()
            if state.owner is None or state.owner.token != token:
                return False
            self._remove()
            return True

    def evict_ownerless(self, made_at: float) -> bool:
        """Remove a bare-mkdir lock, only if it is still the one judged: no record, same mtime."""
        with self._mutex():
            state = self._read()
            if state.kind != "ownerless" or state.made_at != made_at:
                return False
            if (self.path / OWNER_FILE).exists():
                return False
            self._remove()
            return True

    @contextlib.contextmanager
    def _mutex(self) -> Iterator[None]:
        self._config.state_dir.mkdir(parents=True, exist_ok=True)
        with (self._config.state_dir / "lock.mutex").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _read(self) -> LockState:
        try:
            made = self.path.stat().st_mtime
        except FileNotFoundError:
            return LockState("free")
        age = max(0.0, time.time() - made)
        try:
            data = json.loads((self.path / OWNER_FILE).read_text(encoding="utf-8"))
            return LockState("owned", Owner.from_json(data), age, made_at=made)
        except FileNotFoundError:
            return LockState(
                "ownerless", None, age, "held with no owner record (a bare mkdir)", made
            )
        except (OSError, ValueError, TypeError) as exc:
            return LockState("ownerless", None, age, f"owner record unreadable: {exc}", made)

    def _write(self, owner: Owner) -> None:
        temporary = self.path / f".{OWNER_FILE}.{owner.token}.tmp"
        temporary.write_text(json.dumps(owner.to_json(), indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self.path / OWNER_FILE)

    def _remove(self) -> None:
        for leftover in self.path.iterdir():
            if leftover.name == OWNER_FILE or leftover.name.startswith(f".{OWNER_FILE}."):
                leftover.unlink(missing_ok=True)
        self.path.rmdir()


class Verdicts:
    """What the reaper tells the pushing lane: one small file per reaped token."""

    def __init__(self, config: PushGateConfig) -> None:
        self._dir = config.state_dir / "verdicts"

    def write(self, token: str, verdict: dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        temporary = self._dir / f".{token}.tmp"
        temporary.write_text(json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, self._dir / f"{token}.json")

    def read(self, token: str) -> dict[str, Any] | None:
        if not TOKEN.match(token):
            return None
        try:
            found = json.loads((self._dir / f"{token}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return found if isinstance(found, dict) else None

    @staticmethod
    def say(verdict: dict[str, Any]) -> str:
        return (
            f"reaped: hang ({verdict.get('condition')}: {verdict.get('detail')}); "
            f"not a test failure. evidence: {verdict.get('evidence')}"
        )


# --- Killing, evidence, and the reaper --------------------------------------------------


class GroupKiller:
    """Stops one process group: SIGTERM, the grace, then SIGKILL. Never anything else."""

    def __init__(
        self,
        config: PushGateConfig,
        table: ProcessTable,
        signaller: Signaller,
        clock: Clock,
    ) -> None:
        self._config = config
        self._table = table
        self._signaller = signaller
        self._clock = clock

    def signallable(self, pgid: int, require_session: bool = True) -> bool:
        """Never 0, 1 or our own group; by default only a group leading its own session.

        `require_session=False` is for a push traced behind a bare-mkdir lock, whose group
        `OwnerlessHolder` has just proven holds nothing but the push recipe; the group must
        still exist.
        """
        if pgid <= 1 or pgid in {os.getpid(), os.getpgrp()}:
            return False
        if not require_session:
            return self._table.group_alive(pgid)
        return self._table.session_leader(pgid)

    def stop(self, pgid: int, require_session: bool = True) -> str:
        """`refused`, `gone` (already exited), `terminated`, or `killed` (needed SIGKILL)."""
        if not self.signallable(pgid, require_session):
            if not require_session and pgid > 1 and not self._table.group_alive(pgid):
                return "gone"
            return "refused"
        if not self._table.group_alive(pgid):
            return "gone"
        self._signaller.send_group(pgid, signal.SIGTERM)
        deadline = self._clock.now() + self._config.grace_seconds
        while self._clock.now() < deadline:
            if not self._table.group_alive(pgid):
                return "terminated"
            self._clock.sleep(min(0.1, self._config.grace_seconds))
        if self._table.group_alive(pgid) and self.signallable(pgid, require_session):
            self._signaller.send_group(pgid, signal.SIGKILL)
            return "killed"
        return "terminated"


class EvidenceCollector:
    """Writes what a person needs to explain the hang, before anything is killed."""

    def __init__(
        self,
        config: PushGateConfig,
        table: ProcessTable,
        signaller: Signaller,
        clock: Clock,
        which: Callable[[str], str | None] = shutil.which,
        run: Callable[[list[str]], tuple[int, str]] | None = None,
    ) -> None:
        self._config = config
        self._table = table
        self._signaller = signaller
        self._clock = clock
        self._which = which
        self._run = run or self._subprocess

    def collect(self, owner: Owner, decision: Decision) -> Path:
        stamp = datetime.fromtimestamp(self._clock.now(), UTC).strftime("%Y%m%dT%H%M%SZ")
        folder = self._config.state_dir / "evidence" / f"{stamp}-{owner.token[:12]}"
        folder.mkdir(parents=True, exist_ok=True)
        self._json(folder / "owner.json", owner.to_json())
        self._json(
            folder / "decision.json",
            {
                "action": decision.action,
                "condition": decision.condition,
                "detail": decision.detail,
                "measurements": decision.measurements,
            },
        )
        members = self._table.members(owner.pgid) if owner.pgid is not None else []
        (folder / "process-tree.txt").write_text(self._tree(owner, members), encoding="utf-8")
        (folder / "push-log-tail.txt").write_text(self._tail(owner), encoding="utf-8")
        self._stacks(owner, members or [], folder)
        return folder

    def _tree(self, owner: Owner, members: list[Proc] | None) -> str:
        if owner.pgid is None:
            return "no process group was recorded for this push\n"
        if members is None:
            return (
                f"process group {owner.pgid}: the process table could not be read here "
                "(ps refused or failed), so its members are unknown\n"
            )
        lines = [f"process group {owner.pgid}: {len(members)} processes", ""]
        lines.append(f"{'PID':>7} {'PPID':>7} {'PGID':>7} {'CPU-s':>10}  COMMAND")
        for p in members:
            lines.append(f"{p.pid:>7} {p.ppid:>7} {p.pgid:>7} {p.cpu_seconds:>10.2f}  {p.command}")
        return "\n".join(lines) + "\n"

    def _tail(self, owner: Owner) -> str:
        if not owner.log:
            return "(no push log was recorded for this push)\n"
        try:
            with Path(owner.log).open("rb") as stream:
                stream.seek(0, os.SEEK_END)
                stream.seek(max(0, stream.tell() - 512 * 1024))
                text = stream.read().decode("utf-8", errors="replace")
        except OSError as exc:
            return f"(push log unreadable: {exc})\n"
        lines = text.splitlines()[-self._config.log_tail_lines :]
        return "\n".join(lines) + "\n"

    def _stacks(self, owner: Owner, members: list[Proc], folder: Path) -> None:
        targets = [p for p in members if self._is_pytest(p)]
        if not targets:
            (folder / "stacks-unavailable.txt").write_text(
                "no pytest process was found in the group\n", encoding="utf-8"
            )
            return
        spy = self._which("py-spy")
        if spy:
            for p in targets:
                code, out = self._run([spy, "dump", "--pid", str(p.pid)])
                (folder / f"py-spy-{p.pid}.txt").write_text(
                    f"# py-spy dump --pid {p.pid}: exit {code}\n{out}\n", encoding="utf-8"
                )
            return
        if not owner.stacks:
            (folder / "stacks-unavailable.txt").write_text(
                "py-spy is not installed and the push did not arm the suite's SIGUSR1 dump\n",
                encoding="utf-8",
            )
            return
        # Members of the owner's own group only, and only pytest and its workers: they are
        # the processes tests/conftest.py armed to dump on SIGUSR1 rather than die.
        for p in targets:
            self._signaller.send_process(p.pid, signal.SIGUSR1)
        self._clock.sleep(self._config.stack_wait_seconds)
        dumps = folder / "stacks"
        dumps.mkdir(exist_ok=True)
        for found in sorted(Path(owner.stacks).glob("pytest-*.stacks")):
            with contextlib.suppress(OSError):
                shutil.copyfile(found, dumps / found.name)

    @staticmethod
    def _is_pytest(p: Proc) -> bool:
        argv0 = Path(p.command.split(" ", 1)[0]).name.lower() if p.command else ""
        return argv0.startswith("python") and (
            "pytest" in p.command or "sys.stdin.readline" in p.command
        )

    @staticmethod
    def _json(path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")

    @staticmethod
    def _subprocess(argv: list[str]) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 - py-spy by absolute path, fixed arguments
                argv, capture_output=True, text=True, timeout=60
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)
        return done.returncode, done.stdout + done.stderr


@dataclass(frozen=True)
class Traced:
    """What `OwnerlessHolder` found behind a bare-mkdir lock.

    `owner` is None when the holder could not be named unambiguously; `detail` says why.
    """

    owner: Owner | None
    members: list[Proc] | None
    detail: str


class OwnerlessHolder:
    """Names the push behind a bare-mkdir lock, by process, or says it cannot.

    The old recipe -- `until mkdir L; do sleep 20; done; git push ...` -- leaves no owner
    record, and that is the lock that hung on 2026-09-24. The holder is traced, never guessed:

      * exactly one `git push` process, started within `ownerless_match_seconds` of the
        lock's mtime (the recipe pushes on the same line it takes the lock);
      * standing in, or pointed by `git -C` at, one of the declared `worktree_roots`;
      * whose process group holds nothing but that push, its descendants, and the shells
        above it -- the recipe itself. A shell's group can hold anything the shell started;
        a group with any other process in it is not the push's to kill.

    Anything short of that is UNKNOWN, and the reaper never kills on unknown.
    """

    OPTION_WITH_VALUE = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace"})

    def __init__(self, config: PushGateConfig, table: ProcessTable) -> None:
        self._config = config
        self._table = table

    @classmethod
    def is_git_push(cls, command: str) -> bool:
        words = command.split()
        if not words or Path(words[0]).name != "git":
            return False
        skip = False
        for word in words[1:]:
            if skip:
                skip = False
                continue
            if word in cls.OPTION_WITH_VALUE:
                skip = True
                continue
            if word.startswith("-"):
                continue
            return word == "push"
        return False

    def identify(self, made_at: float) -> Traced:
        rows = self._table.processes()
        if rows is None:
            return Traced(None, None, "the process table cannot be read here")
        window = self._config.ownerless_match_seconds
        pushes = [
            p
            for p in rows
            if self.is_git_push(p.command)
            and p.started_at is not None
            and abs(p.started_at - made_at) <= window
            and self._in_worktrees(p)
        ]
        if len(pushes) != 1:
            found = "no push" if not pushes else f"{len(pushes)} pushes"
            return Traced(
                None,
                None,
                f"{found} in the declared worktrees started within {window:g}s of the lock",
            )
        push = pushes[0]
        members = [p for p in rows if p.pgid == push.pgid]
        allowed = self._recipe(push, rows)
        stranger = next((p for p in members if p.pid not in allowed), None)
        if stranger is not None:
            return Traced(
                None,
                members,
                f"group {push.pgid} of pid {push.pid} holds pid {stranger.pid} "
                f"({stranger.command[:60]}), which is outside the push recipe",
            )
        owner = Owner(
            token=f"mkdir-{int(made_at * 1000)}-{push.pid}",
            pid=push.pid,
            pgid=push.pgid,
            dedicated=False,
            uid=os.getuid(),
            branch="(a bare-mkdir push; branch unrecorded)",
            worktree=self._table.cwd(push.pid) or "",
            started_at=made_at,
            command=push.command.split(),
        )
        return Traced(owner, members, f"pid {push.pid} ({push.command[:80]})")

    def _in_worktrees(self, p: Proc) -> bool:
        places = [self._table.cwd(p.pid)]
        words = p.command.split()
        places += [words[i + 1] for i, w in enumerate(words[:-1]) if w == "-C"]
        for place in places:
            if not place:
                continue
            where = Path(place)
            if any(where == root or root in where.parents for root in self._config.worktree_roots):
                return True
        return False

    @staticmethod
    def _recipe(push: Proc, rows: list[Proc]) -> set[int]:
        """The push, everything under it, and the shells above it in its own group."""
        children: dict[int, list[int]] = {}
        by_pid = {p.pid: p for p in rows}
        for p in rows:
            children.setdefault(p.ppid, []).append(p.pid)
        allowed = {push.pid}
        stack = [push.pid]
        while stack:
            for child in children.get(stack.pop(), []):
                if child not in allowed:
                    allowed.add(child)
                    stack.append(child)
        above = by_pid.get(push.ppid)
        while above is not None and above.pgid == push.pgid and above.pid not in allowed:
            if Path(above.command.split(" ", 1)[0]).name not in SHELLS:
                break
            allowed.add(above.pid)
            above = by_pid.get(above.ppid)
        return allowed


class Reaper:
    """One pass: judge the lock's owner against the declared conditions, and act on one."""

    def __init__(
        self,
        config: PushGateConfig,
        lock: PushLock,
        table: ProcessTable,
        evidence: EvidenceCollector,
        killer: GroupKiller,
        clock: Clock,
    ) -> None:
        self._config = config
        self._lock = lock
        self._table = table
        self._evidence = evidence
        self._killer = killer
        self._clock = clock
        self._verdicts = Verdicts(config)
        self._holder = OwnerlessHolder(config, table)

    def tick(self, dry_run: bool = False) -> Decision:
        """One pass, under a non-blocking reap lock: two overlapping passes never both act.

        The standalone schedule and the storm cycle can both start a pass at once, and a
        pass can outlive its interval while it waits out a kill grace. The second simply
        stands aside; every action is keyed to the token (or the mtime) it judged, so a pass
        that runs after another has acted finds nothing left to do.
        """
        self._config.state_dir.mkdir(parents=True, exist_ok=True)
        with (self._config.state_dir / REAP_LOCK).open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return Decision(
                    "none", None, "another reap pass is running; this one stands aside", {}
                )
            try:
                return self._pass(dry_run)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def _pass(self, dry_run: bool) -> Decision:
        state = self._lock.state()
        if state.kind == "free":
            self._forget_samples(keep=None)
            return Decision("none", None, "the push lock is free", {})
        if state.owner is None:
            return self._ownerless(state, dry_run)
        owner = state.owner
        self._forget_samples(keep=owner.token)
        now = self._clock.now()

        if self._stale(owner):
            return self._release_stale(owner, dry_run)
        if owner.pgid is None:
            return Decision("none", None, "the push has not started yet", {}, owner)

        members = self._table.members(owner.pgid)
        held = now - owner.started_at
        if held >= self._config.wall_ceiling_seconds:
            measured = {
                "held_seconds": held,
                "ceiling_seconds": self._config.wall_ceiling_seconds,
            }
            detail = (
                f"held the push lock for {_span(held)}, past the "
                f"{_span(self._config.wall_ceiling_seconds)} ceiling"
            )
            return self._kill(owner, members, "ceiling", detail, measured, dry_run)
        if members is None:
            return Decision(
                "unknown",
                None,
                "the process table cannot be read here, so CPU cannot be sampled; "
                "unknown is never idle",
                {"held_seconds": held},
                owner,
            )
        idle = self._idle(owner, members, now)
        if idle is None:
            return Decision(
                "none",
                None,
                f"held for {_span(held)}; {len(members)} processes, not measured idle",
                {"held_seconds": held, "processes": len(members)},
                owner,
            )
        detail = (
            f"{idle['cpu_seconds']:.2f} CPU-s in {_span(idle['window_seconds'])} across "
            f"{idle['processes']} processes, under the {self._config.idle_cpu_seconds:g} "
            "CPU-s budget"
        )
        return self._kill(owner, members, "idle", detail, idle, dry_run)

    def _ownerless(self, state: LockState, dry_run: bool) -> Decision:
        """A bare-mkdir lock: trace its push by process, or do nothing at all."""
        made = state.made_at if state.made_at is not None else 0.0
        traced = self._holder.identify(made)
        if traced.owner is None or traced.members is None:
            return Decision(
                "unknown",
                None,
                f"{state.detail}, for {_span(state.age_seconds or 0)}; {traced.detail}: "
                "with no holder named unambiguously nothing is done; a person must look",
                {},
            )
        owner, members = traced.owner, traced.members
        self._forget_samples(keep=owner.token)
        now = self._clock.now()
        held = now - made
        if held >= self._config.wall_ceiling_seconds:
            detail = (
                f"bare-mkdir lock held {_span(held)} by {traced.detail}, past the "
                f"{_span(self._config.wall_ceiling_seconds)} ceiling"
            )
            measured = {"held_seconds": held, "ceiling_seconds": self._config.wall_ceiling_seconds}
            return self._kill(owner, members, "ceiling", detail, measured, dry_run, made)
        idle = self._idle(owner, members, now)
        if idle is None:
            return Decision(
                "none",
                None,
                f"bare-mkdir lock held {_span(held)} by {traced.detail}; not measured idle",
                {"held_seconds": held, "processes": len(members)},
                owner,
            )
        detail = (
            f"bare-mkdir lock held by {traced.detail}: {idle['cpu_seconds']:.2f} CPU-s in "
            f"{_span(idle['window_seconds'])} across {idle['processes']} processes, under the "
            f"{self._config.idle_cpu_seconds:g} CPU-s budget"
        )
        return self._kill(owner, members, "idle", detail, idle, dry_run, made)

    # -- the conditions --

    def _stale(self, owner: Owner) -> bool:
        if self._table.alive(owner.pid):
            return False
        if owner.dedicated and owner.pgid is not None:
            # The holder is gone; its push may not be. A group still running is a push in
            # flight, and releasing under it would start a second gate run beside it.
            return not self._table.group_alive(owner.pgid)
        return True

    def _idle(self, owner: Owner, members: list[Proc], now: float) -> dict[str, Any] | None:
        samples = self._samples(owner.token)
        current = {str(p.pid): p.cpu_seconds for p in members}
        samples.append({"t": now, "cpu": current})
        window = self._config.idle_window_seconds
        samples = [s for s in samples if now - s["t"] <= 3 * window][-500:]
        self._save_samples(owner.token, samples)
        if not current:
            return None
        base = None
        for index, sample in enumerate(samples):
            if now - sample["t"] >= window:
                base = index
        if base is None:
            return None
        span = samples[base:]
        pids = set(span[0]["cpu"])
        # A process appearing or vanishing inside the window is activity: a test forking
        # short-lived children spends CPU the survivors never show.
        if any(set(s["cpu"]) != pids for s in span):
            return None
        used = sum(current[pid] - span[0]["cpu"][pid] for pid in pids)
        if used >= self._config.idle_cpu_seconds:
            return None
        return {
            "cpu_seconds": round(used, 3),
            "window_seconds": now - span[0]["t"],
            "processes": len(pids),
            "samples": len(span),
        }

    # -- the actions --

    def _release_stale(self, owner: Owner, dry_run: bool) -> Decision:
        detail = f"holder pid {owner.pid} is gone, and nothing of its push is left running"
        if dry_run:
            return Decision("would-release", "stale", detail, {}, owner)
        decision = Decision("released", "stale", detail, {}, owner)
        folder = self._evidence.collect(owner, decision)
        if not self._lock.evict(owner.token):
            return Decision("none", None, "the lock changed hands while it was judged", {})
        decision = dataclasses.replace(decision, evidence=folder)
        self._record(decision, {"lock": "released"})
        return decision

    def _kill(
        self,
        owner: Owner,
        members: list[Proc] | None,
        condition: str,
        detail: str,
        measured: dict[str, Any],
        dry_run: bool,
        ownerless_made_at: float | None = None,
    ) -> Decision:
        assert owner.pgid is not None
        # A push traced behind a bare-mkdir lock runs in its recipe shell's group, which
        # OwnerlessHolder has just proven holds nothing else; that proof stands in for the
        # group-of-its-own guarantee `run` gives.
        ownerless = ownerless_made_at is not None
        if not owner.dedicated and not ownerless:
            return Decision(
                "refused",
                condition,
                f"{detail}; but the push does not run in a group of its own (it was taken "
                "with `acquire`), so nothing is killed and the lock is kept",
                measured,
                owner,
            )
        for p in members or []:
            hit = next((name for name in self._config.protected if name in p.command), None)
            if hit:
                return Decision(
                    "refused",
                    condition,
                    f"{detail}; but pid {p.pid} in the group matches protected '{hit}', "
                    "so nothing is killed",
                    measured,
                    owner,
                )
        if not self._killer.signallable(owner.pgid, require_session=not ownerless):
            return Decision(
                "refused",
                condition,
                f"{detail}; but group {owner.pgid} no longer leads its own session (its id "
                "may have been reused), so nothing is signalled",
                measured,
                owner,
            )
        if dry_run:
            return Decision("would-kill", condition, detail, measured, owner)
        decision = Decision("killed", condition, detail, measured, owner)
        folder = self._evidence.collect(owner, decision)
        self._verdicts.write(
            owner.token,
            {
                "verdict": "reaped",
                "reason": "hang",
                "condition": condition,
                "detail": detail,
                "evidence": str(folder),
                "time": _iso(self._clock.now()),
            },
        )
        stopped = self._killer.stop(owner.pgid, require_session=not ownerless)
        if ownerless_made_at is not None:
            # The recipe's own `rmdir` died with its shell; the lock is removed here, and
            # only if it is still the bare lock that was judged.
            released = self._lock.evict_ownerless(ownerless_made_at)
        else:
            released = self._lock.evict(owner.token)
        decision = dataclasses.replace(decision, evidence=folder)
        self._record(
            decision,
            {"group": stopped, "lock": "released" if released else "already changed hands"},
            ownerless=ownerless,
        )
        return decision

    def _record(self, decision: Decision, outcome: dict[str, Any], ownerless: bool = False) -> None:
        """One JSON line, appended and flushed: the reap log is never rewritten."""
        owner = decision.owner
        assert owner is not None
        line = {
            "time": _iso(self._clock.now()),
            "condition": decision.condition,
            "action": decision.action,
            "owner": owner.to_json(),
            "branch": owner.branch,
            "detail": decision.measurements,
            "reason": decision.detail,
            "outcome": outcome,
            "evidence": str(decision.evidence),
            "ownerless": ownerless,
        }
        self._config.reap_log.parent.mkdir(parents=True, exist_ok=True)
        with self._config.reap_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(line, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    # -- the samples, kept on disk between passes --

    def _sample_path(self, token: str) -> Path:
        return self._config.state_dir / "samples" / f"{token}.json"

    def _samples(self, token: str) -> list[dict[str, Any]]:
        try:
            found = json.loads(self._sample_path(token).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        return [s for s in found if isinstance(s, dict)] if isinstance(found, list) else []

    def _save_samples(self, token: str, samples: list[dict[str, Any]]) -> None:
        path = self._sample_path(token)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(samples), encoding="utf-8")
        os.replace(temporary, path)

    def _forget_samples(self, keep: str | None) -> None:
        folder = self._config.state_dir / "samples"
        if not folder.is_dir():
            return
        for path in folder.glob("*.json"):
            if path.stem != keep:
                path.unlink(missing_ok=True)


class Status:
    """Who holds the lock and what it is doing, in words."""

    def __init__(
        self, config: PushGateConfig, lock: PushLock, table: ProcessTable, clock: Clock
    ) -> None:
        self._config = config
        self._lock = lock
        self._table = table
        self._clock = clock

    def report(self) -> dict[str, Any]:
        state = self._lock.state()
        found: dict[str, Any] = {"lock": str(self._config.lock), "state": state.kind}
        if state.kind == "ownerless":
            found["detail"] = state.detail
            found["age_seconds"] = state.age_seconds
            traced = OwnerlessHolder(self._config, self._table).identify(state.made_at or 0.0)
            found["traced"] = traced.detail if traced.owner else None
            found["untraced"] = None if traced.owner else traced.detail
        if state.owner is None:
            return found
        owner = state.owner
        found["owner"] = owner.to_json()
        found["held_seconds"] = self._clock.now() - owner.started_at
        found["holder_alive"] = self._table.alive(owner.pid)
        if owner.pgid is not None:
            members = self._table.members(owner.pgid)
            found["group"] = (
                None
                if members is None
                else {
                    "processes": len(members),
                    "cpu_seconds": round(sum(p.cpu_seconds for p in members), 2),
                    "members": [dataclasses.asdict(p) for p in members],
                }
            )
        found["log_tail"] = self._tail(owner)
        return found

    def render(self) -> str:
        found = self.report()
        if found["state"] == "free":
            return f"push lock {found['lock']}: free"
        if found["state"] == "ownerless":
            head = (
                f"push lock {found['lock']}: {found['detail']}, for "
                f"{_span(found.get('age_seconds') or 0)}"
            )
            if found["traced"]:
                return f"{head}\n  traced by process to {found['traced']}"
            return f"{head}\n  holder not identified: {found['untraced']}"
        owner = found["owner"]
        lines = [
            f"push lock {found['lock']}: held for {_span(found['held_seconds'])} by "
            f"{owner['branch']}",
            f"  holder pid {owner['pid']} ({'alive' if found['holder_alive'] else 'GONE'}), "
            f"uid {owner['uid']}, since {owner['started']}",
            f"  worktree {owner['worktree']}",
            f"  command  {' '.join(owner['command'])}",
        ]
        kind = " (its own session)" if owner["dedicated"] else " (the shell's group)"
        if owner["pgid"] is None:
            lines.append("  push group: not started yet")
        elif found.get("group") is None:
            lines.append(f"  push group {owner['pgid']}{kind}: process table unreadable here")
        else:
            group = found["group"]
            lines.append(
                f"  push group {owner['pgid']}"
                f"{kind}: "
                f"{group['processes']} processes, {group['cpu_seconds']:.1f} CPU-s"
            )
            for member in group["members"][:12]:
                lines.append(
                    f"    {member['pid']:>7} {member['cpu_seconds']:>9.2f}s  "
                    f"{member['command'][:100]}"
                )
        if found["log_tail"]:
            lines.append("  last lines of the push log:")
            lines.extend(f"    {line}" for line in found["log_tail"])
        return "\n".join(lines)

    @staticmethod
    def _tail(owner: Owner, count: int = 5) -> list[str]:
        if not owner.log:
            return []
        try:
            text = Path(owner.log).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []
        return text.splitlines()[-count:]


# --- The push -------------------------------------------------------------------------


class PushRunner:
    """Wait for the lock, run the push in a session of its own, and always release."""

    def __init__(self, config: PushGateConfig, lock: PushLock, clock: Clock) -> None:
        self._config = config
        self._lock = lock
        self._clock = clock
        self._stopped: int | None = None
        self._child: subprocess.Popen[bytes] | None = None
        self._wait_timeout: float | None = None
        self._push_timeout: float | None = None
        self._timed_out = False

    def run(
        self,
        argv: list[str],
        wait: bool = True,
        wait_timeout: float | None = None,
        push_timeout: float | None = None,
    ) -> int:
        """The push's own exit status; 124 reaped, 125 past `push_timeout`, 3 never got the lock.

        `wait_timeout` bounds the wait for the lock and `push_timeout` the push itself, so a
        caller with its own deadline (lane-publish.py) never has to kill this wrapper -- which
        would leave its lock for the reaper to find -- to stop waiting.
        """
        self._wait_timeout = wait_timeout
        self._push_timeout = push_timeout
        self._timed_out = False
        token = uuid.uuid4().hex
        uid = os.getuid()
        logs = self._config.state_dir / "logs"
        stacks = self._config.state_dir / "stacks" / token
        branch, worktree = _where()
        with self._on_signal():
            owner = self._take(token, uid, argv, branch, worktree, logs, stacks, wait)
            if owner is None:
                return 128 + self._stopped if self._stopped else HELD_EXIT
            try:
                returncode = self._push(owner, argv, logs / f"{token}.log", stacks)
            finally:
                self._lock.release(token, uid)
        verdict = Verdicts(self._config).read(token)
        if verdict is not None and returncode != 0:
            print(Verdicts.say(verdict), flush=True)
            return REAPED_EXIT
        if self._timed_out:
            print(f"push-gate: the push ran past its {self._push_timeout:g}s limit", flush=True)
            return PUSH_TIMEOUT_EXIT
        if self._stopped:
            return 128 + self._stopped
        return returncode if returncode >= 0 else 128 - returncode

    def _take(
        self,
        token: str,
        uid: int,
        argv: list[str],
        branch: str,
        worktree: str,
        logs: Path,
        stacks: Path,
        wait: bool,
    ) -> Owner | None:
        announced: str | None = None
        waited_total = 0.0
        while self._stopped is None:
            owner = Owner(
                token=token,
                pid=os.getpid(),
                pgid=None,
                dedicated=True,
                uid=uid,
                branch=branch,
                worktree=worktree,
                started_at=self._clock.now(),
                command=list(argv),
                log=str(logs / f"{token}.log"),
                stacks=str(stacks),
            )
            if self._lock.acquire(owner):
                return owner
            state = self._lock.state()
            holder = state.owner.token if state.owner else state.kind
            if holder != announced:
                announced = holder
                who = (
                    f"{state.owner.branch} (pid {state.owner.pid})"
                    if state.owner
                    else state.detail or state.kind
                )
                print(f"push-gate: waiting for {self._config.lock}, held by {who}", flush=True)
            if not wait:
                return None
            if self._wait_timeout is not None and waited_total >= self._wait_timeout:
                print(
                    f"push-gate: gave up after waiting {_span(waited_total)} for the lock",
                    flush=True,
                )
                return None
            waited = 0.0
            while waited < self._config.poll_seconds and self._stopped is None:
                step = min(0.2, self._config.poll_seconds)
                self._clock.sleep(step)
                waited += step
            waited_total += waited
        return None

    def _push(self, owner: Owner, argv: list[str], log: Path, stacks: Path) -> int:
        if self._stopped is not None:
            return 128 + self._stopped
        log.parent.mkdir(parents=True, exist_ok=True)
        child = subprocess.Popen(  # nosec B603 - the caller's own push command, no shell
            argv,
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, STACKS_ENV: str(stacks)},
        )
        self._child = child
        if self._stopped is not None:
            self._stop_child()
        self._lock.update(dataclasses.replace(owner, pgid=child.pid))
        with log.open("ab") as sink:
            reader = threading.Thread(target=self._tee, args=(child, sink), daemon=True)
            reader.start()
            try:
                returncode = child.wait(timeout=self._push_timeout)
            except subprocess.TimeoutExpired:
                self._timed_out = True
                self._stop_child()
                returncode = child.wait()
            # A process that escaped the group may still hold the pipe; the push is over.
            reader.join(timeout=5)
        return returncode

    @staticmethod
    def _tee(child: subprocess.Popen[bytes], sink: Any) -> None:
        assert child.stdout is not None
        for chunk in iter(child.stdout.readline, b""):
            with contextlib.suppress(OSError, ValueError):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                sink.write(chunk)
                sink.flush()

    def _stop_child(self) -> None:
        child = self._child
        if child is None or child.poll() is not None:
            return
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(child.pid, signal.SIGTERM)

        def escalate() -> None:
            if child.poll() is None:
                with contextlib.suppress(ProcessLookupError, PermissionError):
                    os.killpg(child.pid, signal.SIGKILL)

        timer = threading.Timer(self._config.grace_seconds, escalate)
        timer.daemon = True
        timer.start()

    @contextlib.contextmanager
    def _on_signal(self) -> Iterator[None]:
        """SIGTERM, SIGINT and SIGHUP stop the push's group and still release the lock."""
        if threading.current_thread() is not threading.main_thread():
            yield
            return

        def stop(signum: int, frame: object) -> None:
            if self._stopped is None:
                self._stopped = signum
                self._stop_child()

        caught = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        previous = {sig: signal.signal(sig, stop) for sig in caught}
        try:
            yield
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)


class Schedule:
    """The reaper's own schedule, declared as code and installed by one command.

    Hangs happen whenever anyone pushes, not only while the storm cycle runs, so the reaper
    has a schedule of its own: a launchd agent on macOS, a systemd user timer on Linux, or a
    printed cron line where neither exists. The units are tracked templates in `templates/`
    (12.c); installing renders them with this machine's paths and the lock this tool
    resolved, so the schedule reaps exactly the lock its installer meant. Kubernetes has no
    CronJob here on purpose: nothing pushes from inside the cluster, and a reaper can only
    see processes on its own machine.
    """

    TEMPLATES = Path(__file__).absolute().parent / "templates"
    TARGETS = ("launchd", "systemd", "cron")

    def __init__(
        self,
        config: PushGateConfig,
        root: Path,
        tool: Path,
        python: str,
        target: str | None = None,
        home: Path | None = None,
        run: Callable[[list[str]], tuple[int, str]] | None = None,
    ) -> None:
        self._config = config
        self._root = root
        self._tool = tool
        self._python = python
        self._target = target or ("launchd" if sys.platform == "darwin" else "systemd")
        if self._target not in self.TARGETS:
            raise SystemExit(f"push-gate: unknown schedule target {self._target!r}")
        self._home = home or Path.home()
        self._run = run or EvidenceCollector._subprocess
        self._label = config.schedule_label

    def values(self) -> dict[str, str]:
        return {
            "label": self._label,
            "python": self._python,
            "tool": str(self._tool),
            "root": str(self._root),
            "lock": str(self._config.lock),
            "interval": str(int(self._config.schedule_seconds)),
            "path": self._config.schedule_path,
            "log": str(self._config.state_dir / "reaper.log"),
        }

    def files(self) -> dict[Path, str]:
        """Every file the schedule consists of, rendered, keyed by where it is installed."""
        values = self.values()
        if self._target == "launchd":
            escaped = {key: escape(value) for key, value in values.items()}
            where = self._home / "Library/LaunchAgents" / f"{self._label}.plist"
            return {where: self._render("push-gate-reaper.plist", escaped)}
        if self._target == "systemd":
            units = self._home / ".config/systemd/user"
            return {
                units / f"{self._label}.service": self._render("push-gate-reaper.service", values),
                units / f"{self._label}.timer": self._render("push-gate-reaper.timer", values),
            }
        return {}

    def cron_line(self) -> str:
        v = self.values()
        # cron's finest grain is a minute; the schedule's own interval is not expressible.
        return (
            f"* * * * * {v['python']} {v['tool']} --root {v['root']} --lock {v['lock']} "
            f"reap >> {v['log']} 2>&1"
        )

    def install(self, dry_run: bool = False) -> list[str]:
        if self._target == "cron":
            return [
                "cron has no minute finer than one; add this line with `crontab -e` "
                "(this tool never edits a crontab):",
                self.cron_line(),
            ]
        lines = []
        for path, text in self.files().items():
            lines.append(f"{'would write' if dry_run else 'wrote'} {path}")
            if not dry_run:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")
        if not dry_run:
            self._config.state_dir.mkdir(parents=True, exist_ok=True)
        for argv, required in self._load_commands():
            lines.append(self._command(argv, required, dry_run))
        return lines

    def uninstall(self, dry_run: bool = False) -> list[str]:
        if self._target == "cron":
            return ["remove the push-gate line from `crontab -e`:", self.cron_line()]
        lines = [self._command(argv, False, dry_run) for argv in self._unload_commands()]
        for path in self.files():
            if path.exists():
                lines.append(f"{'would remove' if dry_run else 'removed'} {path}")
                if not dry_run:
                    path.unlink()
        if self._target == "systemd":
            lines.append(self._command(["systemctl", "--user", "daemon-reload"], False, dry_run))
        return lines

    def status(self) -> str:
        if self._target == "cron":
            return "cron: see `crontab -l` for the line `install-schedule --target cron` prints"
        missing = [path for path in self.files() if not path.exists()]
        if missing:
            return f"{self._target}: not installed ({missing[0]} is absent)"
        if self._target == "launchd":
            code, _ = self._run(["launchctl", "print", f"gui/{os.getuid()}/{self._label}"])
        else:
            code, _ = self._run(["systemctl", "--user", "is-active", f"{self._label}.timer"])
        state = "installed and loaded" if code == 0 else "installed but not loaded"
        every = int(self._config.schedule_seconds)
        return f"{self._target}: {self._label} {state}; one reap pass every {every}s"

    def _load_commands(self) -> list[tuple[list[str], bool]]:
        if self._target == "launchd":
            [plist] = self.files()
            domain = f"gui/{os.getuid()}"
            return [
                (["launchctl", "bootout", f"{domain}/{self._label}"], False),
                (["launchctl", "bootstrap", domain, str(plist)], True),
            ]
        return [
            (["systemctl", "--user", "daemon-reload"], True),
            (["systemctl", "--user", "enable", "--now", f"{self._label}.timer"], True),
        ]

    def _unload_commands(self) -> list[list[str]]:
        if self._target == "launchd":
            return [["launchctl", "bootout", f"gui/{os.getuid()}/{self._label}"]]
        return [["systemctl", "--user", "disable", "--now", f"{self._label}.timer"]]

    def _command(self, argv: list[str], required: bool, dry_run: bool) -> str:
        shown = " ".join(argv)
        if dry_run:
            return f"would run: {shown}"
        code, out = self._run(argv)
        if code == 0 or not required:
            return f"ran: {shown}" + ("" if code == 0 else f" (exit {code}; nothing to undo)")
        return f"FAILED: {shown}: exit {code}: {out.strip()[-160:]}"

    def _render(self, name: str, values: dict[str, str]) -> str:
        template = (self.TEMPLATES / name).read_text(encoding="utf-8")
        return string.Template(template).substitute(values)


def _inside_checkout(root: Path) -> bool:
    """Whether `root` is inside a git checkout. Module-level: one stateless git question.

    A storm root is not a checkout; the tracked copy of this folder is. From there the
    derived lock would be private to that checkout -- a lock that excludes nobody -- so
    `main` refuses rather than derive one.
    """
    try:
        done = subprocess.run(  # nosec B603 B607 - git with fixed arguments
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0 and done.stdout.strip() == "true"


def _where() -> tuple[str, str]:
    """The branch and worktree the push runs from. Module-level: two git reads, no state."""

    def git(*args: str) -> str | None:
        try:
            done = subprocess.run(  # nosec B603 B607 - git with fixed arguments
                ["git", *args], capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return done.stdout.strip() if done.returncode == 0 and done.stdout.strip() else None

    return (
        git("rev-parse", "--abbrev-ref", "HEAD") or "(unknown branch)",
        git("rev-parse", "--show-toplevel") or str(Path.cwd()),
    )


def main(argv: list[str] | None = None) -> int:
    """The command line. Module-level because a script's entry point is one by definition."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--root", type=Path, help="the storm root holding storm.toml")
    parser.add_argument("--lock", type=Path, help="the lock directory, for this run only")
    commands = parser.add_subparsers(dest="command", required=True)
    status = commands.add_parser("status", help="who holds the lock, and what it is doing")
    status.add_argument("--json", action="store_true")
    acquire = commands.add_parser("acquire", help="take the lock; print the release token")
    acquire.add_argument("--wait", action="store_true", help="wait for a held lock")
    acquire.add_argument("--pid", type=int, help="the holder (default: the calling shell)")
    release = commands.add_parser("release", help="give the lock back (its owner only)")
    release.add_argument("token")
    run = commands.add_parser("run", help="wait, run the push, always release")
    run.add_argument("--no-wait", action="store_true")
    run.add_argument("--wait-timeout", type=float, help="give up waiting after this long")
    run.add_argument("--push-timeout", type=float, help="stop the push after this long")
    run.add_argument("push", nargs=argparse.REMAINDER, help="-- git push ...")
    reap = commands.add_parser("reap", help="one reaper pass")
    reap.add_argument("--dry-run", action="store_true", help="report; change nothing")
    for name, text in (
        ("install-schedule", "install the reaper's own schedule (launchd, systemd or cron)"),
        ("uninstall-schedule", "remove it"),
        ("schedule-status", "say whether it is installed and loaded"),
    ):
        verb = commands.add_parser(name, help=text)
        verb.add_argument("--target", choices=Schedule.TARGETS)
        verb.add_argument(
            "--python", help="the interpreter the schedule runs (default: this one), 3.11+"
        )
        if name != "schedule-status":
            verb.add_argument("--dry-run", action="store_true", help="show; change nothing")
    args = parser.parse_args(argv)

    root = (args.root or storm_paths.storm(__file__)).absolute()
    chosen = args.lock or (Path(os.environ[LOCK_ENV]) if os.environ.get(LOCK_ENV) else None)
    if chosen is None and "lock" not in _section(root) and _inside_checkout(root):
        print(
            f"push-gate: {root} is inside a git checkout, not a storm root, so the push lock "
            f"it would derive is private to this checkout and excludes nobody. Run the "
            f"storm root's copy (<storm>/tools/push_gate.py), or name the machine's shared "
            f"lock with {LOCK_ENV}=<dir> or --lock <dir>.",
            file=sys.stderr,
        )
        return 2
    config = PushGateConfig.declared(root, lock=chosen)
    clock = Clock()
    lock = PushLock(config, clock)
    table = ProcessTable()

    if args.command == "status":
        report = Status(config, lock, table, clock)
        print(json.dumps(report.report(), indent=2) if args.json else report.render())
        return 0
    if args.command == "acquire":
        holder = args.pid or os.getppid()
        branch, worktree = _where()
        owner = Owner(
            token=uuid.uuid4().hex,
            pid=holder,
            pgid=os.getpgid(holder),
            dedicated=False,
            uid=os.getuid(),
            branch=branch,
            worktree=worktree,
            started_at=clock.now(),
            command=["acquire"],
        )
        while not lock.acquire(dataclasses.replace(owner, started_at=clock.now())):
            if not args.wait:
                print(Status(config, lock, table, clock).render(), file=sys.stderr)
                return HELD_EXIT
            clock.sleep(config.poll_seconds)
        print(owner.token)
        return 0
    if args.command == "release":
        verdict = Verdicts(config).read(args.token)
        outcome = lock.release(args.token, os.getuid())
        if verdict is not None:
            print(Verdicts.say(verdict), file=sys.stderr)
            return REAPED_EXIT
        if outcome == "not-owner":
            print("push-gate: refused: the lock is not held by that token", file=sys.stderr)
            return 1
        return 0
    if args.command == "run":
        push = args.push[1:] if args.push[:1] == ["--"] else args.push
        if not push:
            parser.error("run needs a command: run -- git push ...")
        return PushRunner(config, lock, clock).run(
            push,
            wait=not args.no_wait,
            wait_timeout=args.wait_timeout,
            push_timeout=args.push_timeout,
        )
    if args.command in {"install-schedule", "uninstall-schedule", "schedule-status"}:
        schedule = Schedule(
            config,
            root,
            Path(__file__).absolute(),
            args.python or sys.executable,
            target=args.target,
        )
        if args.command == "schedule-status":
            print(schedule.status())
            return 0
        verb = schedule.install if args.command == "install-schedule" else schedule.uninstall
        lines = verb(dry_run=args.dry_run)
        print("\n".join(lines))
        return 1 if any(line.startswith("FAILED") for line in lines) else 0
    signaller = Signaller()
    reaper = Reaper(
        config,
        lock,
        table,
        EvidenceCollector(config, table, signaller, clock),
        GroupKiller(config, table, signaller, clock),
        clock,
    )
    decision = reaper.tick(dry_run=args.dry_run)
    print(decision.line(), flush=True)
    if decision.action in {"released", "killed", "would-release", "would-kill"}:
        return 1
    return 2 if decision.action in {"unknown", "refused"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
