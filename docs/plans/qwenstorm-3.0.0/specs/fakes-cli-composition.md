## Title
test(cli): every outside collaborator of the CLI — local PostgreSQL, PATH, subprocess, TUI, operator, sleep, SIGTERM latch — comes from CliComposition

## Why
`fakes-job-wakeup` introduced `CliComposition` (`src/vibey/cli/composition.py`), reached through
`click`'s context object. It holds only `open_app` so far. `tests/cli/test_operational_commands.py`
still patches 18 names in `vibey.cli.main` and the stdlib, because `cli/main.py` reaches them
directly:

| patched name | count | where `cli/main.py` reaches it |
|---|---|---|
| `vibey.cli.main.PostgresLocalService` | 4 | `:1173`, `:1248` |
| `shutil.which` | 3 | `:1349-1365` |
| `vibey.cli.main.subprocess.run` | 2 | `:1488` (the login check) |
| `vibey.tui.dashboard.VibeyDashboardApp` and `VibeyReplayApp` | 5 + 1 | `:606-652` |
| `vibey.infrastructure.operator.run` | 1 | `:1409` |
| `vibey.cli.main.asyncio.sleep` | 1 | `:1559` |
| `vibey.cli.main.SIGTERM_LATCH` | 1 | `:1537-1538` |

`tests/cli/test_main.py:56,75` replaces `cli_main._enqueue_design` and `cli_main._work_once`.

## Required behaviour
1. **`CliComposition` gains keyword-only fields,** each with its production default, and
   `CliCompositionInterface` mirrors them:
   - `postgres_local: Callable[[], PostgresLocalServiceInterface]`, defaulting to
     `PostgresLocalService` (`infrastructure/postgres.py:134`; its interface exists or is
     added beside it);
   - `locator: ExecutableLocator = PATH_LOCATOR` (`fakes-process-executor`);
   - `runner: SyncCommandRunner = SUBPROCESS_RUNNER`;
   - `dashboard_app: Callable[..., DashboardAppInterface]`, defaulting to `VibeyDashboardApp`,
     and `replay_app` likewise. Use `tui/interfaces/` for the interface if one exists;
     otherwise declare a minimal one there with the `run()` the CLI calls;
   - `operator_runner: Callable[..., None]`, defaulting to `vibey.infrastructure.operator.run`;
   - `sleep: Callable[[float], Awaitable[None]] = asyncio.sleep`;
   - `sigterm: SigtermLatchInterface = SIGTERM_LATCH` (`cli/interfaces/early_signals_interface.py`).
2. **`cli/main.py`** reads each of these from `CliComposition.current()` at the sites in the
   table, and nowhere else. The latch is still **armed at import** (`:7-9`). That placement is
   the fix for PID 1 losing SIGTERM (`pyproject.toml` E402 comment). Only its later *reads*
   (`release`, `fired`) go through the composition.
3. **`tests/fakes/cli.py`**:
   - `FakePostgresLocalService` implements `PostgresLocalServiceInterface`. It has a
     scripted `status()`, records `start()`, `stop()` and `install()`, and can fail each on cue;
   - `RecordingTuiApp(**kwargs)` records the constructor kwargs and `run()` calls. It is
     used for both apps;
   - `RecordingOperatorRunner` records the `namespace` it was run with;
   - `InstantSleep` returns at once and records the durations;
   - `FakeSigtermLatch` has `fired: bool`, and records `release()`;
   - register each for its interface, and add the new interfaces to `DRIVER_SEAMS`.
4. **Switch the 18 patches** in `test_operational_commands.py` to `obj=CliComposition(...)` with
   these fakes. Where a test also patched the notifier, it already uses
   `_ComposedWithFakeWakeup` (`fakes-job-wakeup`); combine them in one composition.
   `tests/cli/test_main.py`: replace the two `monkeypatch.setattr` with an `InMemoryApp`
   composition (`tests/fakes/app.py`), and assert on the fake queue's jobs instead of on a
   stub.
5. Lower both files' baseline entries.
6. **`CliComposition` becomes the one `ctx.obj`.** Two earlier lanes each put their own seam
   object in `ctx.obj`, chosen by `isinstance`: `installer-doctor`'s `LocalStackFactory` and
   `split-380-2-doctor-cli`'s `DoctorSeams` (whose chain also accepts a `LocalStackFactory`).
   Whichever of them has landed (grep `cli/main.py` and `cli/doctor_loops.py` for
   `isinstance(ctx.obj,`), this lane absorbs it:
   - `CliComposition` gains `local_stack: LocalStackFactory | None = None` and
     `doctor: DoctorSeams = field(default_factory=DoctorSeams)`;
   - each `isinstance(ctx.obj, LocalStackFactory)` / `isinstance(ctx.obj, DoctorSeams)` reader
     becomes a read of `CliComposition.current().local_stack` / `.doctor` (a `None`
     `local_stack` keeps the production `LocalStackComposition()`);
   - every test that passes `obj=LocalStackFactory(...)` or `obj=DoctorSeams(...)` passes
     `obj=CliComposition(local_stack=...)` / `obj=CliComposition(doctor=...)` instead.
   Afterwards `grep -rn "isinstance(ctx.obj" src/vibey/cli` prints nothing: `ctx.obj` holds one
   object type. If neither lane has landed, record that in the commit body and do nothing here.

## Where to change
- `src/vibey/cli/composition.py`, `src/vibey/cli/interfaces/composition_interface.py`, `src/vibey/cli/main.py`
  (the sites in the table), and the `tui/interfaces/` or `infrastructure/` interface files if one must be declared.
- New `tests/fakes/cli.py`, `tests/fakes/test_fake_cli.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/cli/test_operational_commands.py`, `tests/cli/test_main.py`.

## Acceptance criteria
- [ ] `grep -cE 'patch\(|setattr\(' tests/cli/test_operational_commands.py tests/cli/test_main.py` prints `0` for both files.
- [ ] `SIGTERM_LATCH.arm()` is still the first statement after the imports it needs in `cli/main.py` (`:7-9`).
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
- `tests/fakes/test_fake_cli.py`, one behaviour test per fake:
  - `test_postgres_local_fake_scripts_status_and_failures`
  - `test_tui_app_records_kwargs_and_run`
  - `test_instant_sleep_records`
  - `test_sigterm_fake`
- `tests/cli/test_composition.py` (appended): `test_every_collaborator_defaults_to_production`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Taking `test_operational_commands.py` off PostgreSQL (`fakes-cli-operational-1..3`).
  Its tests stay `integration` here.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-bootstrap-seam`, `fakes-process-executor`, `fakes-operator-k8s`.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `src/vibey/cli/main.py` (R-lanes and T15; this lane edits only the listed sites).
- **Must keep passing unchanged:** the SIGTERM tests (`tests/cli/test_early_signals*` if
  present, and the drain tests) and the protected tests.
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

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
