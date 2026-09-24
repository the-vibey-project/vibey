## Title
feat(test-harness): one test run at a time on a machine, held by every process of the run

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-277`): the harness runs "one
test run at a time on one machine … Nothing starts a second test run beside a running one".
Draft ADR-0045 §2 makes an exclusive `flock` on `<state_dir>/machine.lock` the floor that both
backends and the pytest plugin take.

The descriptor is handed to the run's child through `pass_fds`, so the lock is held until the
**last** process of the run exits, even if the process that took it is SIGKILLed. That gives
the invariant the rest of the design relies on: *a lock holder that finds an attempt recorded
`running` knows its recorder is dead* (ADR-0045 §2, §9). A holder file names who holds the
lock, so `vibey test status` and a waiting requester can say whom they wait for. `fcntl` and
`os` are stdlib: no new dependency (ADR-0045 §13).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/machine_lock.py`:
1. **`MachineLock(path: Path, *, poll_seconds: float = 0.2)`**.
   `async def acquire(self, *, timeout_seconds: float, holder: Mapping[str, object]) -> MachineLockHold | None`:
   1. `self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)`;
   2. `fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)`;
   3. loop: try `fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)`. On `BlockingIOError`, if
      `time.monotonic() - start >= timeout_seconds`, `os.close(fd)` and return `None`; otherwise
      `await asyncio.sleep(self._poll_seconds)`. `timeout_seconds == 0` is a single try;
   4. on success write `<path>.holder.json` (the lock path with `.holder.json` appended, e.g.
      `machine.lock.holder.json`) atomically: a temporary file in the same directory created with
      mode `0o600`, then `os.replace`. Its content is `json.dumps({"pid": os.getpid(), "since": datetime.now(UTC).isoformat(), **holder})`;
   5. return `MachineLockHold(fd, holder_path, os.getpid())`.

   An `OSError` from steps 1–2 (an unwritable directory) propagates unchanged: callers decide
   how to degrade (harness-T07).
2. **`MachineLockHold(fd: int, holder_path: Path, pid: int)`** has the property `fd -> int` and
   `release(self) -> None`, which is idempotent: it removes the holder file only if that file
   still names this pid, then calls `fcntl.flock(fd, fcntl.LOCK_UN)` and `os.close(fd)`. Its
   docstring says: `release()` must be called only after every process that inherited the
   descriptor has exited, because `LOCK_UN` releases the open file description they share.
3. **`MachineLock.holder(self) -> dict[str, object] | None`** reads and parses the holder file
   and adds `"alive": bool` from `os.kill(pid, 0)` (`ProcessLookupError` → `False`,
   `PermissionError` → `True`). It returns `None` when the file is missing, unreadable, not a JSON
   object, or has no integer `pid`.
4. **The interface** `src/vibey/infrastructure/test_harness/interfaces/machine_lock_interface.py`
   declares `@runtime_checkable` `MachineLockInterface` (`acquire`, `holder`) and
   `MachineLockHoldInterface` (`fd` property, `release`).
5. **Registry (amendment A4).** `tests/fakes/registry.py` (lane fakes-registry) is data only:
   `REGISTRY` (`FakeRegistration(port, build, note)`), `PENDING` (a port's `__qualname__` → the
   lane that owes its fake) and `DRIVER_SEAMS` (the infrastructure seams that must be registered
   or pending). Import `from vibey.infrastructure.test_harness.interfaces import machine_lock_interface`,
   append `machine_lock_interface.MachineLockInterface` to the `DRIVER_SEAMS` tuple, and add
   `"MachineLockInterface": "fakes-test-harness"` to `PENDING`. Lane fakes-test-harness later
   registers `InMemoryMachineLock` and deletes the entry. `MachineLockHoldInterface` is returned,
   never injected, so it is not a seam.

## Where to change
- New `src/vibey/infrastructure/test_harness/machine_lock.py` and
  `src/vibey/infrastructure/test_harness/interfaces/machine_lock_interface.py`.
- `tests/fakes/registry.py` (two entries and one import, with `edit_file`).
- New `tests/infrastructure/test_harness/test_machine_lock.py`.

## Acceptance criteria
- [ ] A second descriptor on the same path cannot take the lock while the first holds it, within one process (`flock` locks an open file description).
- [ ] A child that inherited the descriptor (`pass_fds`) keeps the lock after the parent closes its own descriptor **without** `LOCK_UN`, and the lock frees when the child exits. This is the ADR-0045 *Verification owed* item for macOS and Linux (8.h: both default OSes).
- [ ] The holder file names the pid and the given fields, and reports liveness.
- [ ] `uv run pytest -q -p no:cacheprovider tests/fakes` passes (the seam is pending).
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_machine_lock.py`; every lock path is under `tmp_path`:
- `test_acquire_and_release_round_trip`
- `test_second_acquire_times_out_while_held`
- `test_zero_timeout_is_a_single_try`
- `test_lock_survives_the_parent_when_a_child_inherits_it`: acquire, spawn
  `subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"], pass_fds=(hold.fd,))`,
  then `os.close(hold.fd)`. A fresh `acquire(timeout_seconds=0.3)` returns `None`. Wait for the
  child; then `acquire(timeout_seconds=1)` succeeds.
- `test_holder_reports_pid_fields_and_liveness`
- `test_holder_is_none_when_missing_or_malformed` (parametrized: missing, not JSON, a list, no pid)
- `test_release_is_idempotent_and_keeps_a_foreign_holder_file`
- `test_an_unwritable_directory_raises_oserror` (a `tmp_path` directory with mode `0o500`; skip when running as root)
- `test_lock_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Using the lock (harness-T07, T13, T14). The in-memory fake (fakes-test-harness).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T05-test-harness-config, fakes-registry.
- **Files touched:** the two new source files, `tests/fakes/registry.py`, the new test file.
- **Shares a file with:** `tests/fakes/registry.py` (every fakes lane and the seam-declaring harness lanes append to it; append, never reorder).
- **Must keep passing unchanged:** harness-T05's tests, `tests/infrastructure/process/*`, `tests/fakes/*`, `tests/meta/*`, and the protected tests.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at a declared seam. Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`/`AsyncMock`/`Mock` (`tests/meta/test_patching_ratchet.py` refuses any in a new file); `setenv`, `delenv` and `chdir` are allowed.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); a child of `sys.executable` is inside.
  - Never touch the real machine lock: every lock and state directory is under `tmp_path`.
  - No test waits longer than 5 s. POSIX only.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
