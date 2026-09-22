## Title
fix(test-harness): with nothing running and no writable state directory, a routed pytest announces it and runs directly

## Why
The operator's standard is that `pytest` in a clone with nothing running must pass. Draft
ADR-0045 already degrades the *broker* (`auto` selects `local` when no harness service
consumes the queue, §3). Two local prerequisites have no degrade:
1. **The state directory.** T07's `locked` mode (`specs/test-harness-lanes.md:1046-1100`) and
   T17's `queue` mode open `<state_dir>/machine.lock`. The default `state_dir` is
   `$XDG_STATE_HOME/vibey/test-harness` or `~/.local/state/vibey/test-harness` (§14). A
   sandboxed or read-only home, a CI container or a model's worktree sandbox raises
   `PermissionError` or `OSError` there. After T07, every root pytest would then fail before
   running a test.
2. **The configured command's executable.** `[test_harness] command` defaults to
   `uv run --no-sync pytest`. In a clone without `uv` on `PATH`, the local backend's
   supervisor would dead-letter every run as `unexecutable` (T13 behaviour 2.2), so a plain
   `pytest` fails with exit 3.

T17 says a broken harness "must neither pass silently nor run unrouted" (T17 behaviour 2.5).
Amendment A6 separates a **missing prerequisite** from a **broken harness**:
- a missing prerequisite (no broker, no writable state directory, no command executable) is
  announced on one line, and the run proceeds **directly in this process**. It is not
  serialised and not recorded;
- a broken harness, meaning any other exception, still exits 3.
The announcement is evidence (10.f), so the degrade is not silent. It is the same posture as
`auto`'s broker degrade.

## Required behaviour
1. **In `src/vibey/cli/pytest_route.py`, a class `HarnessPrerequisites`**, with an interface
   beside it:
   - `check(self, settings: TestHarnessSettingsInterface) -> str | None` returns `None` when
     the local harness can run. Otherwise it returns a one-line reason;
   - the state directory is checked by creating it (`mkdir(parents=True, exist_ok=True, mode=0o700)`)
     and opening `machine.lock` for append. An `OSError` gives
     `f"no writable state_dir {path} ({exc.strerror})"`;
   - the command's executable is resolved with the `ExecutableLocator`
     (`fakes-process-executor`). A missing executable gives
     `f"the test command's executable {name!r} is not on PATH"`;
   - it takes the locator by constructor keyword, and does no other I/O.
2. **`PytestHarnessRoute`** gains `prerequisites: HarnessPrerequisitesInterface | None = None`.
   In `locked` and `queue` modes, before anything else, it runs `reason = prerequisites.check(settings)`.
   When `reason` is set, it writes
   `vibey test-harness: {reason}; running directly (not serialised, not recorded)` to stderr,
   sets `VIBEY_HARNESS_RUN=direct-<pid>` so that nested runs pass through, and returns `None`,
   so pytest runs in this process. Any exception after the check keeps T17's exit 3.
3. **T09's real-database test becomes opt-in.** In
   `tests/infrastructure/test_harness/test_environment_probe.py`, mark
   `test_database_version_against_the_test_database` `@pytest.mark.integration`. It relies on
   `tests/conftest.py` setting `VIBEY_TEST_DATABASE_URL` for every session, which stopped with
   `fakes-harness-decouple`. Make it skip when the variable is unset.
4. **The route tests.** Append to `tests/cli/test_pytest_route.py`:
   - `test_an_unwritable_state_dir_runs_directly_and_says_so` (a `tmp_path` directory with mode `0o500`);
   - `test_a_missing_command_executable_runs_directly_and_says_so` (`FakeExecutableLocator({})`);
   - `test_a_broken_harness_still_exits_3` (a composition that raises after the check);
   - `test_end_to_end_direct_run_with_nothing_running`. This is a subprocess: a scratch
     project with `vibey_harness_route = queue`, `VIBEY_HARNESS_STATE_DIR` pointing at an
     unwritable directory, and `PATH` without `uv`. It passes, and stderr has the
     announcement line.

## Where to change
- `src/vibey/cli/pytest_route.py`, `src/vibey/cli/interfaces/pytest_route_interface.py`.
- `tests/cli/test_pytest_route.py` (appended), `tests/infrastructure/test_harness/test_environment_probe.py` (one mark).

## Acceptance criteria
- [ ] With the root ini on `locked` or `queue`, `HOME` read-only and no `uv` on `PATH`,
      `python -m pytest -q -p no:cacheprovider tests/domain` passes and prints the announcement once.
- [ ] A real harness defect still exits 3, with T17's message.
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
The four route tests in behaviour 4, plus
`test_prerequisites_report_the_first_missing_one` in `tests/cli/test_pytest_route.py`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli/test_pytest_route.py tests/infrastructure/test_harness tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The broker degrade (T25 owns `auto`). The route flip (T28).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `harness-T17-pytest-queue-route`, `harness-T09-environment-probe`,
  `fakes-process-executor`, `fakes-harness-decouple`.
- **Must land before:** `harness-T28-route-flip`. See amendment A6. If the operator folds A6
  into T07 and T17 before filing them, this lane only adds the tests, and verifies that the
  behaviour is present.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every other T07 and T17 test, and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).
  - The T-lanes' standing constraints apply too:
    - import modules, not `Test*` names, in test files;
    - point `VIBEY_HARNESS_STATE_DIR` at `tmp_path` in every test that builds settings, a
      lock or a store, and strip `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE` from every
      child environment, so that no test touches the real machine lock;
    - use hermetic commands (`sys.executable`), and no test waits longer than 5 s.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
