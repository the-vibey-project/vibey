"""What the push gate promises, declared beside `push_gate.py` (sub-doctrine 9.b).

Declares; never consumes. `tests/meta/test_storm_push_gate.py` holds each class to its
Protocol -- and the fakes the tests drive it with to the seams they stand in for -- so the
declaration cannot drift from the class it describes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PushGateConfigInterface(Protocol):
    """Where the lock and its records are, and every declared threshold (12.c)."""

    lock: Path
    state_dir: Path
    reap_log: Path
    idle_cpu_seconds: float
    idle_window_seconds: float
    wall_ceiling_seconds: float
    grace_seconds: float
    poll_seconds: float
    log_tail_lines: int
    stack_wait_seconds: float
    protected: tuple[str, ...]
    ownerless_match_seconds: float
    worktree_roots: tuple[Path, ...]
    schedule_seconds: float
    schedule_label: str
    schedule_path: str


@runtime_checkable
class OwnerInterface(Protocol):
    """The record inside the lock: who holds it, and the group the push runs in."""

    token: str
    pid: int
    pgid: int | None
    dedicated: bool
    uid: int
    branch: str
    worktree: str
    started_at: float
    command: list[str]
    log: str | None
    stacks: str | None

    def to_json(self) -> dict[str, Any]:
        """The record as written to `owner.json` and to the reap log."""
        ...


@runtime_checkable
class ClockInterface(Protocol):
    """Wall-clock time, and waiting."""

    def now(self) -> float:
        """Seconds since the epoch."""
        ...

    def sleep(self, seconds: float) -> None:
        """Wait."""
        ...


@runtime_checkable
class ProcessTableInterface(Protocol):
    """Read-only questions about processes. `members` is None when it cannot be known."""

    def alive(self, pid: int) -> bool:
        """Whether `pid` exists."""
        ...

    def group_alive(self, pgid: int) -> bool:
        """Whether any process of group `pgid` exists."""
        ...

    def members(self, pgid: int) -> Any:
        """The group's processes with their CPU time; None when the table is unreadable."""
        ...

    def listing(self) -> str | None:
        """The whole table, for a person; None when it is unreadable."""
        ...

    def session_leader(self, pgid: int) -> bool:
        """Whether `pgid` is still the group a push started in a session of its own."""
        ...

    def processes(self) -> Any:
        """Every process with its start time; None when the table is unreadable."""
        ...

    def cwd(self, pid: int) -> str | None:
        """Where `pid` stands; None when that cannot be read."""
        ...


@runtime_checkable
class SignallerInterface(Protocol):
    """The only side-effecting seam: signals, to a group or to one of its members."""

    def send_group(self, pgid: int, sig: int) -> None:
        """Signal every process in group `pgid`."""
        ...

    def send_process(self, pid: int, sig: int) -> None:
        """Signal one process."""
        ...


@runtime_checkable
class PushLockInterface(Protocol):
    """The shared lock: an atomic mkdir with the owner's record inside."""

    def acquire(self, owner: Any) -> bool:
        """Take the lock for `owner`; False when somebody holds it."""
        ...

    def update(self, owner: Any) -> bool:
        """Rewrite the record, only for the token that holds the lock."""
        ...

    def state(self) -> Any:
        """free, owned (with the owner), or ownerless."""
        ...

    def release(self, token: str, uid: int) -> str:
        """released, not-owner, or free."""
        ...

    def evict(self, token: str) -> bool:
        """The reaper's release: only if the lock still carries `token`."""
        ...

    def evict_ownerless(self, made_at: float) -> bool:
        """Remove a bare-mkdir lock, only if it is still the one judged (same mtime)."""
        ...


@runtime_checkable
class GroupKillerInterface(Protocol):
    """Stops one process group: SIGTERM, the grace, SIGKILL."""

    def signallable(self, pgid: int, require_session: bool = True) -> bool:
        """Whether `pgid` may be signalled as a push's own group."""
        ...

    def stop(self, pgid: int, require_session: bool = True) -> str:
        """refused, gone, terminated or killed."""
        ...


@runtime_checkable
class OwnerlessHolderInterface(Protocol):
    """Names the push behind a bare-mkdir lock by process, or says it cannot."""

    def identify(self, made_at: float) -> Any:
        """The traced owner and its group, or None with the reason."""
        ...


@runtime_checkable
class ScheduleInterface(Protocol):
    """The reaper's own schedule: launchd, systemd, or a printed cron line."""

    def files(self) -> dict[Path, str]:
        """Every unit file, rendered, keyed by where it is installed."""
        ...

    def install(self, dry_run: bool = False) -> list[str]:
        """Write and load the schedule; what was done, line by line."""
        ...

    def uninstall(self, dry_run: bool = False) -> list[str]:
        """Unload and remove it."""
        ...

    def status(self) -> str:
        """Installed, loaded, and how often."""
        ...


@runtime_checkable
class EvidenceCollectorInterface(Protocol):
    """Writes what a person needs to explain a hang, before anything is killed."""

    def collect(self, owner: Any, decision: Any) -> Path:
        """The evidence folder for this reap."""
        ...


@runtime_checkable
class ReaperInterface(Protocol):
    """One pass over the lock's owner against the declared conditions."""

    def tick(self, dry_run: bool = False) -> Any:
        """The decision, having acted on it unless `dry_run`."""
        ...


@runtime_checkable
class VerdictsInterface(Protocol):
    """What the reaper tells the pushing lane."""

    def write(self, token: str, verdict: dict[str, Any]) -> None:
        """Record that `token`'s push was reaped."""
        ...

    def read(self, token: str) -> dict[str, Any] | None:
        """The verdict for `token`, if its push was reaped."""
        ...


@runtime_checkable
class StatusInterface(Protocol):
    """Who holds the lock and what it is doing."""

    def report(self) -> dict[str, Any]:
        """Machine-readable."""
        ...

    def render(self) -> str:
        """In words."""
        ...


@runtime_checkable
class PushRunnerInterface(Protocol):
    """Wait for the lock, run the push in a session of its own, always release."""

    def run(
        self,
        argv: list[str],
        wait: bool = True,
        wait_timeout: float | None = None,
        push_timeout: float | None = None,
    ) -> int:
        """The push's exit status; 124 when the reaper ended it."""
        ...
