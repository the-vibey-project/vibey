## Title
test(cli): the worker, recover, watch and operator command tests run on the in-memory app, and the PostgreSQL-only file is gone

## Why
The last third of `tests/cli/test_operational_commands.py` is 42 tests: from
`test_worker_invalid_engine` (formerly `:1420`) through `test_recover_with_project`
(formerly `:2301`).

These are the tests that exercise the worker loop:
- claim, handle, reap and wait for the notifier;
- engine and provider selection;
- draining on SIGTERM (`test_worker_drains*`);
- the `--once` path;
- the sweeps, `watch`, `operator` and `recover`.

By this lane every collaborator is injected:
- the wakeup is `InMemoryJobWakeupOpener`;
- `sleep` is `InstantSleep`, and `sigterm` is `FakeSigtermLatch`;
- `operator_runner` is `RecordingOperatorRunner`.
So a worker test can drive the real `WorkerLoop` over the in-memory queue and prove it drains.

## Required behaviour
1. **`tests/cli/test_ops_worker.py`** (new) holds the tests from `test_worker_invalid_engine`
   through `test_recover_with_project`, moved as lanes 1 and 2 moved theirs.
   - Worker tests build the composition with `InMemoryJobWakeupOpener` over the factory's
     notifier, `sleep=InstantSleep()` and `sigterm=FakeSigtermLatch(...)`.
   - A drain test makes the latch fire after N iterations with a `fire_after: int`
     constructor argument on `FakeSigtermLatch`. The latch counts each read of `fired`, and
     reports `True` from the Nth read on. Add that argument to `tests/fakes/cli.py` if it is
     not already there.
   - Engine tests use `ScriptedEngine` adapters (`fakes-engines`) through
     `resources.engine_adapters`, or through the composition field that selects engines if the
     command builds them itself.
2. **`test_operational_commands.py` is deleted** when it holds no test. Any test that
   genuinely needs PostgreSQL moves instead to `tests/cli/test_ops_postgres.py`, marked
   `integration`, with the reason in its docstring.
3. **Baseline.** Remove the old file's entry. The new modules count zero.
4. **`tests/meta/test_integration_tier.py`'s `PER_TEST_MODULES`** (`fakes-harness-decouple`):
   remove any key that no longer exists.

## Where to change
- New `tests/cli/test_ops_worker.py`, `tests/cli/test_ops_postgres.py` (only if needed);
  `tests/cli/ops_support.py`, `tests/fakes/cli.py` (the `fire_after` hook);
  `tests/cli/test_operational_commands.py` (deleted); `tests/meta/patching_baseline.json`;
  `tests/meta/test_integration_tier.py`.

## Acceptance criteria
- [ ] `test -e tests/cli/test_operational_commands.py` fails, or the file holds only
      `integration` tests that each name their reason.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli` passes with PostgreSQL stopped.
- [ ] The total collected in `tests/cli` equals the count before `fakes-cli-operational-1`.
- [ ] 100% `cli/` coverage from the **default tier alone**:
      `uv run pytest -q -p no:cacheprovider -m "not integration and not paid" --cov=vibey --cov-branch --cov-report= && uv run coverage report --include='src/vibey/cli/*' --fail-under=100`.
      If it falls short, list the uncovered lines in the commit body.

## Tests to write first (TDD)
- Move and pass one test at a time. Add `test_worker_drains_when_the_latch_fires_after_two_iterations`
  if no moved test covers the drain on the in-memory queue.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli tests/meta
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider -m "not integration and not paid" --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Production code. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-operational-2`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** the protected tests. SIGTERM behaviour is covered by the
  moved drain tests, which must still pass.
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
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
