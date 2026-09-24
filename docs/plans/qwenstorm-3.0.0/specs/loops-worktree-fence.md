## Title
feat(loop-service): a worktree fence on the shared volume makes supersede work across both loops
ADR-0046 lane L25 (slug `loops-worktree-fence`).

## Why
Draft ADR-0046 (`STORM/specs/ADR-two-loops.md`, *Context*, lines 55–58) records two defects in the superseded host's supersede design (R22 rule 3g, `specs/rmq-r22-loop-service-host.md`; closing note `issue-audit/updates/369.md`): supersede cannot fire at the default prefetch 1, because the successor is not delivered while the orphan holds its delivery; and the "one run per worktree" guard is per service instance, so after a job moves from one loop to the other, two runs can edit one worktree. ADR-0046 §6 replaces rule 3g with a **worktree fence** on the shared volume, used by every seat host of both loops: `<cwd>/.vibey/run.lock`, created exclusively and holding its holder, plus `<cwd>/.vibey/supersede.json`, a high-water attempt per supersede key. Its §3 idempotency table makes it the owner of "run ownership", and its *Verification owed* V-FS1 asks this lane to test that exclusive creation is atomic on a local disk. *Security impact*: the fence writes only inside `<cwd>/.vibey/`, and breaking a stale lock renames it aside, never deleting a holder's evidence.

The design sheet specifies `os.open(..., O_CREAT|O_EXCL)` and then writing the holder. That leaves a moment when the lock exists but is empty, and a racing reader would read it as unreadable and break it as stale, so two runs would both acquire. This lane creates the lock **already holding its content**: the holder is written to a temporary file in `.vibey/`, then `os.link(temp, run.lock)`, which is atomic and fails with `FileExistsError` when the lock exists (the classic lock technique, also safe on NFS). The V-FS1 test below races two threads for this reason.

## Required behaviour
All in `src/vibey/infrastructure/loop_service/worktree_lock.py`.
1. **Value types:**
   ```python
   class FenceOutcome(StrEnum):
       ACQUIRED = "acquired"
       SUPERSEDED = "superseded"
       BUSY = "busy"
       BUSY_SUPERSEDING = "busy_superseding"


   @dataclass(frozen=True, slots=True)
   class FenceHolder:
       """Who holds a worktree: the run, its supersede key and attempt, and its deadline."""

       run_id: UUID
       key: str | None
       attempt: int
       loop_id: str
       instance: str
       run_dir: str | None
       started_at: datetime
       deadline_at: datetime

       def __post_init__(self) -> None:
           if self.attempt < 0:
               raise ValueError("FenceHolder.attempt must be at least 0")
           if self.started_at.tzinfo is None or self.deadline_at.tzinfo is None:
               raise ValueError("FenceHolder times must be timezone-aware")


   @dataclass(frozen=True, slots=True)
   class FenceDecision:
       outcome: FenceOutcome
       holder_run_id: UUID | None = None
       broke_stale: bool = False
   ```
2. **`class WorktreeFence`**, built as `WorktreeFence(*, stale_after: timedelta, clock: Clock, inbox_factory: Callable[[Path], RunInboxInterface] = RunInbox, logger: Logger | None = None)`. Class constants `LOCK = "run.lock"`, `MARKS = "supersede.json"`, `MARKS_LOCK = "supersede.lock"`. `logger` defaults to `structlog.get_logger(__name__)`.
3. **`acquire(self, cwd: Path, holder: FenceHolder) -> FenceDecision`:**
   ```python
   directory = cwd / ".vibey"
   directory.mkdir(parents=True, exist_ok=True)
   if self._below_high_water(directory, holder):
       return FenceDecision(FenceOutcome.SUPERSEDED)
   return self._take(directory, holder, may_break=True)
   ```
   - `_below_high_water(self, directory: Path, holder: FenceHolder) -> bool`: returns `False` at once when `holder.key is None` (no supersede files are touched). Otherwise, under an exclusive `fcntl.flock` of `directory / MARKS_LOCK` (opened with `os.open(path, os.O_CREAT | os.O_RDWR, 0o600)`, closed in `finally`, which releases the lock), read the marks; when `high = marks.get(holder.key)` is not `None` and `holder.attempt < high`, return `True`; otherwise set `marks[holder.key] = holder.attempt`, write the marks, and return `False`. (Raising the mark before the run lock is taken is what makes an orphan's later redelivery SUPERSEDED.)
   - `_read_marks(self, path: Path) -> dict[str, int]`: `FileNotFoundError` → `{}`; `OSError` or `ValueError` while reading or decoding, or JSON that is not a `dict` → log `warning("worktree_supersede_marks_unreadable", path=str(path))` and return `{}`; otherwise `{str(key): value for key, value in raw.items() if isinstance(value, int) and not isinstance(value, bool)}`.
   - `_write_marks(self, path: Path, marks: Mapping[str, int]) -> None`: write `json.dumps(dict(marks), sort_keys=True)` to `path.with_name(f"{path.name}.{uuid4().hex}.tmp")`, then `os.replace` it onto `path`.
   - `_take(self, directory: Path, holder: FenceHolder, *, may_break: bool) -> FenceDecision`:
     ```python
     lock = directory / self.LOCK
     if self._claim(lock, holder):
         return FenceDecision(FenceOutcome.ACQUIRED, broke_stale=not may_break)
     existing = self._read_holder(lock)
     if existing is not None and existing.run_id == holder.run_id:
         return FenceDecision(FenceOutcome.ACQUIRED)  # a redelivery of the run that holds it
     if may_break and (existing is None or self._clock.now() > existing.deadline_at + self._stale_after):
         self._break(lock, existing)
         return self._take(directory, holder, may_break=False)
     if (
         existing is not None
         and holder.key is not None
         and existing.key == holder.key
         and existing.attempt < holder.attempt
     ):
         run_dir = None if existing.run_dir is None else Path(existing.run_dir)
         if run_dir is not None and run_dir.resolve().is_relative_to(directory.parent.resolve()):
             # The holder's own inbox, on the shared volume: this works from either loop.
             self._inbox_factory(run_dir).write_stop()
         return FenceDecision(FenceOutcome.BUSY_SUPERSEDING, holder_run_id=existing.run_id)
     return FenceDecision(
         FenceOutcome.BUSY, holder_run_id=None if existing is None else existing.run_id
     )
     ```
     The `is_relative_to(cwd)` check means a lock file whose `run_dir` was tampered with can never make the fence write outside the worktree (*Security impact*).
   - `_claim(self, lock: Path, holder: FenceHolder) -> bool`:
     ```python
     temp = lock.with_name(f"{lock.name}.{holder.run_id}.{uuid4().hex}.tmp")
     descriptor = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
     with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
         handle.write(json.dumps(self._encode(holder), sort_keys=True))
     try:
         # link() creates the lock with its content already in it, and fails when the
         # lock exists: no reader ever sees an empty lock (V-FS1).
         os.link(temp, lock)
     except FileExistsError:
         return False
     finally:
         temp.unlink()
     return True
     ```
   - `_encode(self, holder: FenceHolder) -> dict[str, object]`: `{"run_id": str(run_id), "key": key, "attempt": attempt, "loop_id": loop_id, "instance": instance, "run_dir": run_dir, "started_at": started_at.isoformat(), "deadline_at": deadline_at.isoformat()}`.
   - `_read_holder(self, lock: Path) -> FenceHolder | None`: inside one `try`, `raw = json.loads(lock.read_text(encoding="utf-8"))` and return `FenceHolder(run_id=UUID(raw["run_id"]), key=raw["key"], attempt=int(raw["attempt"]), loop_id=str(raw["loop_id"]), instance=str(raw["instance"]), run_dir=raw["run_dir"], started_at=datetime.fromisoformat(raw["started_at"]), deadline_at=datetime.fromisoformat(raw["deadline_at"]))`; `except (OSError, ValueError, KeyError, TypeError)` → `None` (a missing, unreadable or naive-dated lock reads as `None`).
   - `_break(self, lock: Path, existing: FenceHolder | None) -> None`: the lock is renamed aside, never deleted:
     ```python
     stamp = self._clock.now().astimezone(UTC).strftime("%Y%m%dT%H%M%S%fZ")
     aside = lock.with_name(f"{lock.name}.stale-{stamp}-{uuid4().hex[:8]}")
     with contextlib.suppress(FileNotFoundError):
         lock.rename(aside)
     self._log.warning(
         "worktree_lock_stale_broken",
         cwd=str(lock.parent.parent),
         holder_run_id=None if existing is None else str(existing.run_id),
         renamed_to=str(aside),
     )
     ```
     (The sheet names the aside `run.lock.stale-<utc ts>`; the 8-hex suffix is added so two breaks in one microsecond, or under a fixed test clock, can never overwrite each other's evidence.)
4. **`release(self, cwd: Path, run_id: UUID) -> bool`**: read the holder of `cwd / ".vibey" / LOCK`; when it is `None` or its `run_id != run_id`, return `False` and change nothing; otherwise `lock.unlink(missing_ok=True)` and return `True`.
5. **`high_water(self, cwd: Path, key: str) -> int | None`**: `self._read_marks(cwd / ".vibey" / MARKS).get(key)`.
6. The fence writes only inside `<cwd>/.vibey/` (lock, marks, their temp files, stale asides), plus the one `stop` file in a holder's inbox under the same `cwd`. Files it creates are mode `0o600` (the lock, via `os.open`; the marks inherit the umask).
7. **Interface** `src/vibey/infrastructure/loop_service/interfaces/worktree_lock_interface.py`: `@runtime_checkable class WorktreeFenceInterface(Protocol)` with `acquire(self, cwd: Path, holder: FenceHolder) -> FenceDecision`, `release(self, cwd: Path, run_id: UUID) -> bool`, `high_water(self, cwd: Path, key: str) -> int | None`. Follow `src/vibey/infrastructure/db/interfaces/migrator_interface.py:10-17`: `from __future__ import annotations`, and import `FenceDecision`, `FenceHolder` under `if TYPE_CHECKING:` from `vibey.infrastructure.loop_service.worktree_lock`, so the interface has no runtime dependency on the code that implements it.
8. **In-memory fake**, appended to `tests/fakes/loops.py` (no staleness: it has no clock, which its docstring says):
   ```python
   class InMemoryWorktreeFence:
       """WorktreeFenceInterface in memory, keyed by str(cwd). It never breaks a stale lock
       (it has no clock); a superseding stop is recorded in `stops`, not written."""

       def __init__(self) -> None:
           self.holders: dict[str, FenceHolder] = {}
           self.marks: dict[tuple[str, str], int] = {}
           self.stops: list[UUID] = []

       def acquire(self, cwd: Path, holder: FenceHolder) -> FenceDecision:
           place = str(cwd)
           if holder.key is not None:
               high = self.marks.get((place, holder.key))
               if high is not None and holder.attempt < high:
                   return FenceDecision(FenceOutcome.SUPERSEDED)
               self.marks[(place, holder.key)] = holder.attempt
           existing = self.holders.get(place)
           if existing is None or existing.run_id == holder.run_id:
               self.holders[place] = holder
               return FenceDecision(FenceOutcome.ACQUIRED)
           if holder.key is not None and existing.key == holder.key and existing.attempt < holder.attempt:
               self.stops.append(existing.run_id)
               return FenceDecision(FenceOutcome.BUSY_SUPERSEDING, holder_run_id=existing.run_id)
           return FenceDecision(FenceOutcome.BUSY, holder_run_id=existing.run_id)

       def release(self, cwd: Path, run_id: UUID) -> bool:
           existing = self.holders.get(str(cwd))
           if existing is None or existing.run_id != run_id:
               return False
           del self.holders[str(cwd)]
           return True

       def high_water(self, cwd: Path, key: str) -> int | None:
           return self.marks.get((str(cwd), key))
   ```
9. **Registry**: `WorktreeFenceInterface` is appended to `DRIVER_SEAMS`; `REGISTRY` gains `FakeRegistration(port=WorktreeFenceInterface, build=InMemoryWorktreeFence)`.

## Where to change
Line 1 of every new file is the provenance comment, copied byte for byte from line 1 of `src/vibey/infrastructure/process/reaper.py`.
- **Precondition.** `test -f src/vibey/infrastructure/engines/run_dir.py` must succeed (R20 child 1); if not, stop and report `blocked: the run-dir lane has not landed`.
- **New** `src/vibey/infrastructure/loop_service/worktree_lock.py`. Imports: `contextlib`, `fcntl`, `json`, `os`, `from collections.abc import Callable, Mapping`, `from dataclasses import dataclass`, `from datetime import UTC, datetime, timedelta`, `from enum import StrEnum`, `from pathlib import Path`, `from uuid import UUID, uuid4`, `structlog`, `from vibey.application.interfaces import Clock, Logger`, `from vibey.infrastructure.engines.interfaces.run_dir_interface import RunInboxInterface`, `from vibey.infrastructure.engines.run_dir import RunInbox`. `__all__ = ["FenceDecision", "FenceHolder", "FenceOutcome", "WorktreeFence"]`. Module docstring: ADR-0046 §6's fence; atomic creation by `link` (why, in one sentence); writes only inside `<cwd>/.vibey/`.
- **New** `src/vibey/infrastructure/loop_service/interfaces/worktree_lock_interface.py` (behaviour 7).
- **`tests/fakes/loops.py`**: add `from vibey.infrastructure.loop_service.worktree_lock import FenceDecision, FenceHolder, FenceOutcome` (and `Path`, `UUID` if missing) to its import block with `edit_file`; append the class of behaviour 8 at the end with `edit_file`.
- **`tests/fakes/registry.py`**: run the registration script of lane `loops-result-store` ("Where to change", the `register_fakes.py` block) with only these lists, then delete the script:
  ```python
  IMPORTS = [
      "from tests.fakes.loops import InMemoryWorktreeFence",
      "from vibey.infrastructure.loop_service.interfaces.worktree_lock_interface import WorktreeFenceInterface",
  ]
  SEAMS = ["WorktreeFenceInterface"]
  ENTRIES = ["FakeRegistration(port=WorktreeFenceInterface, build=InMemoryWorktreeFence)"]
  ```
- Then `uv run ruff check --fix` and `uv run ruff format` on `tests/fakes/loops.py tests/fakes/registry.py src/vibey/infrastructure/loop_service tests/infrastructure/loop_service`.
- **New** `tests/infrastructure/loop_service/test_worktree_lock.py`.

## Acceptance criteria
- [ ] Two threads racing `acquire` on one worktree get exactly one `ACQUIRED`, twenty rounds in a row (V-FS1, local case).
- [ ] A stale or unreadable lock is renamed to `run.lock.stale-*` with its content intact, never deleted.
- [ ] After every scenario, every file the fence created lies under `<cwd>/.vibey/`, except a superseding `stop` in the holder's inbox under the same `cwd`.
- [ ] No `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`; `tests/meta/patching_baseline.json` does not change; `tests/fakes/test_port_parity.py` passes.
- [ ] 100% branch coverage of `src/vibey/infrastructure/*`.

## Tests to write first (TDD)
`tests/infrastructure/loop_service/test_worktree_lock.py`. Helpers:
```python
NOW = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)

class _Clock:
    """A Clock (application/interfaces/system.py) the test sets by hand."""

    def __init__(self, instant: datetime) -> None:
        self.instant = instant

    def now(self) -> datetime:
        return self.instant

def _fence(clock: _Clock | None = None) -> WorktreeFence:
    return WorktreeFence(stale_after=timedelta(seconds=300), clock=clock or _Clock(NOW))

def _holder(*, key: str | None = None, attempt: int = 0, run_dir: str | None = None,
            deadline: datetime = NOW + timedelta(hours=1), run_id: UUID | None = None) -> FenceHolder:
    return FenceHolder(run_id=run_id or uuid4(), key=key, attempt=attempt, loop_id="sovereignloop",
                       instance="host-1", run_dir=run_dir, started_at=NOW, deadline_at=deadline)
```
Each test uses a fresh `cwd = tmp_path / "wt"` (created). Logs are read with `structlog.testing.capture_logs()`.
- `test_first_run_acquires_and_writes_its_holder`: `ACQUIRED`, `broke_stale is False`; `.vibey/run.lock` decodes to the holder's `_encode` fields; its mode is `0o600` (`stat.S_IMODE`); no `*.tmp` file remains in `.vibey/`.
- `test_a_redelivery_of_the_holding_run_acquires_again`: the same holder twice → `ACQUIRED` both times, and the lock is unchanged.
- `test_an_attempt_below_the_high_water_is_superseded`: key `"job-1"` attempt 2 acquires and releases; attempt 1 → `SUPERSEDED`, and no lock exists; `high_water(cwd, "job-1") == 2`; `high_water(cwd, "other")` is `None`.
- `test_a_lower_attempt_holding_the_worktree_is_stopped_through_its_inbox`: attempt 0 of `"job-1"` holds with `run_dir=str(cwd / ".sovereignloop/runs/r0")`; attempt 1 → `BUSY_SUPERSEDING` with `holder_run_id` = the first run id, and exactly one `inbox/*-stop.json` under that run dir; a holder without `run_dir`, superseded the same way, gets `BUSY_SUPERSEDING` and no inbox is created.
- `test_a_tampered_run_dir_outside_the_worktree_gets_no_stop`: a lower attempt holding with `run_dir=str(tmp_path / "elsewhere")` → `BUSY_SUPERSEDING`, and `tmp_path / "elsewhere"` does not exist.
- `test_another_key_or_no_key_is_busy`: a holder of `"job-1"` blocks a holder of `"job-2"` and a holder with no key: both `BUSY` with its run id.
- `test_a_stale_lock_is_renamed_aside_and_acquired`: a holder with `deadline=NOW - timedelta(hours=2)` holds; a new holder → `ACQUIRED`, `broke_stale is True`; exactly one `run.lock.stale-*` exists and still holds the old holder's JSON; one `worktree_lock_stale_broken` warning with `holder_run_id` = the old run id. A holder whose deadline is only 100 s past (inside `stale_after`) keeps the worktree `BUSY`.
- `test_an_unreadable_lock_is_broken_as_stale`: `.vibey/run.lock` holds `"garbage"` → `ACQUIRED`, `broke_stale is True`, the aside holds `"garbage"`, and the warning's `holder_run_id` is `None`.
- `test_release_unlinks_only_the_holders_own_lock`: `release(cwd, other_id)` is `False` and the lock stays; `release(cwd, holder.run_id)` is `True` and the lock is gone; a second `release` is `False`.
- `test_unreadable_marks_are_logged_and_read_as_empty`: `.vibey/supersede.json` holding `"not json"`, then `["x"]`: `high_water` is `None` and `worktree_supersede_marks_unreadable` is logged; a key-bearing `acquire` then rewrites the marks as a valid `{key: attempt}`.
- `test_everything_it_writes_is_inside_dot_vibey`: after acquire, supersede, break-stale and release on one `cwd`, every path under `cwd` other than the holder's `run_dir/inbox` lies under `cwd / ".vibey"`.
- `test_two_threads_racing_acquire_get_exactly_one`: twenty rounds, each on a fresh `cwd` and a fresh fence: two `threading.Thread`s wait on one `threading.Barrier(2)`, then each calls `acquire` with its own holder (no key); `sorted(outcomes) == [FenceOutcome.ACQUIRED, FenceOutcome.BUSY]`.
- `test_fence_holder_refuses_a_negative_attempt_and_naive_times`: `ValueError` for `attempt=-1` and for a naive `started_at`.
- `test_the_fence_and_its_fake_satisfy_the_interface`: `isinstance` of `_fence()` and `InMemoryWorktreeFence()` against `WorktreeFenceInterface`. The fake: first holder `ACQUIRED`; the same run again `ACQUIRED`; a lower attempt of the same key after a higher one `SUPERSEDED`; a higher attempt while a lower one holds `BUSY_SUPERSEDING` with `stops == [lower run id]`; another key `BUSY`; `release` by a stranger `False`, by the holder `True`; `high_water` returns the mark.

## Checks the lane must run (all must pass)
```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict src/vibey
uv run lint-imports
uv run bandit -q -r src/vibey
uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/fakes tests/meta/test_patching_ratchet.py tests/application/test_interfaces_convention.py
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
git status --short
```
`fcntl.flock` and `os.link` are POSIX and behave the same on Arch Linux and macOS (8.h, `src/vibey_tools/gh/docs/doctrines.md:326-334`). The NFS (ReadWriteMany) half of V-FS1 is a cluster-smoke contract owed by lane L37's follow-up, not this lane.

## Out of scope
- Calling the fence from the seat host (lane `loops-seat-host-fence`), and the `SUPERSEDE` control broadcast (lanes `loops-seat-host-drain`, `loops-control-and-dead-letters`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees. Protected tests (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`) are never edited.
- Do not push, open a PR or change remotes. Commit locally with the Title as the subject. Follow `STORM/EDITING-RULES.md`.

**Depends on:** `loops-result-store`, `split-367-1-run-dir`
- `loops-result-store`: the `loop_service` package, its `.importlinter` entry, the loop fakes module and the registration script.
- `split-367-1-run-dir` (unfiled spec `specs/split-367-1-run-dir.md`, slug `split-367-1-run-dir`): `RunInbox` and `RunInboxInterface`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
