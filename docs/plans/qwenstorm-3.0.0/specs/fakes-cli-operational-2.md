## Title
test(cli): the work-once, deploy, doctor and install command tests run on the in-memory app

## Why
The second third of `tests/cli/test_operational_commands.py` is 42 tests: from
`test_work_once_unknown_provider` (formerly `:609`) through
`test_worker_continuous_processes_then_waits` (formerly `:1391`). It covers `work-once`,
the `deploy` group (status, inspect, plan, rollback, cancel), `doctor` (record, cluster),
`install-postgres` and `enqueue-design`.

`fakes-cli-operational-1` created `tests/cli/ops_support.py` (the `memory_app` fixture,
`invoke`, and the seed helpers). This lane moves the next third there, exactly as lane 1 did.

## Required behaviour
1. **`tests/cli/test_ops_work_deploy_doctor.py`** (new) holds the tests between
   `test_work_once_unknown_provider` and `test_worker_continuous_processes_then_waits`,
   inclusive. Locate them by name, since lane 1 shifted the line numbers. They are moved, not
   rewritten: the same names, output and exit codes.
   - The `_fast_engine_preflight` fixture (formerly `:1231`) moves to `ops_support.py` if it
     is used here.
   - `install-postgres` and `doctor` tests pass `postgres_local=FakePostgresLocalService(...)`,
     `locator=FakeExecutableLocator(...)` and `runner=ScriptedSyncCommandRunner(...)` through
     `ops.invoke(..., **kw)`.
   - `work-once` tests seed jobs through `resources.jobs` and assert on
     `app.factory.persistence.jobs` (the shared `InMemoryQueueStore`).
   - The deploy tests use `FaultyCloudClient` and `InMemoryDeploymentStateStore` where the
     command reads them. If the command builds its cloud client from `--azure-client memory`,
     that production `InMemoryAzureClientAdapter` is already in memory.
2. **Add the seed helpers** these tests need to `ops_support.py`, over the port methods only.
3. **Delete the moved tests** from the old file with checked replacements.
4. Anything that genuinely needs PostgreSQL stays in the old file, marked `integration`, with
   the reason in the commit body.
5. Lower the old file's baseline entry.

## Where to change
- New `tests/cli/test_ops_work_deploy_doctor.py`; `tests/cli/ops_support.py`;
  `tests/cli/test_operational_commands.py` (deletions); `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] The new module passes with PostgreSQL stopped (`-m "not integration"`).
- [ ] The total collected in `tests/cli` is unchanged.
- [ ] 100% `cli/` coverage.

## Tests to write first (TDD)
- Move and pass one test at a time.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_ops_work_deploy_doctor.py tests/cli/test_ops_status_ledger.py tests/meta
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The worker, recover, watch and operator tests (lane 3). Production code.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-operational-1`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the tests left in the old file, `test_ops_status_ledger.py`, and the protected tests.
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
