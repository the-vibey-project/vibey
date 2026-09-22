## Title
feat(measure): the BUILD handlers pass the composed measurement port to every engine run

## Why
Lane `gap-measure-engine-runs-1` taught `run_and_record` to measure a run when it is given a
`MeasurementPort` and a clock. Nothing gives it one yet, so every engine run is still unmeasured,
which sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) calls incomplete. The two
callers are `BuildImplementHandler` (`src/vibey/application/build_implement_handler.py:64-95`,
call at `:232-239`) and `BuildVerifyHandler` (`build_verify_handler.py:163-191`, call at
`:256-263`); both already hold a required `clock`. The composition root builds them in
`build_full_worker` (`src/vibey/bootstrap.py:439-473`) and has held `resources.measurements`
since lane `gap-measure-ledger-sink`.

## Required behaviour
1. `BuildImplementHandler.__init__` gains the keyword parameter
   `measurements: MeasurementPort | None = None` (after `tracer`, `:80`), stored as
   `self._measurements`. Its `run_and_record(...)` call (`:232-239`) passes
   `measurements=self._measurements, clock=self._clock`.
2. `BuildVerifyHandler.__init__` gains the same parameter (after `tracer`, `:176`); its call
   (`:256-263`) passes the same two keywords.
3. `build_full_worker` (`src/vibey/bootstrap.py`) passes `measurements=resources.measurements` to
   both constructors (`BuildImplementHandler(` at `:442`, `BuildVerifyHandler(` at `:460`).
4. With `measurements=None` (every existing test's construction) behaviour is unchanged.

## Where to change
- `src/vibey/application/build_implement_handler.py`, `src/vibey/application/build_verify_handler.py`,
  `src/vibey/bootstrap.py` (each with `edit_file`; a few lines each).
- Append one test to each of `tests/application/test_build_implement_handler.py` and
  `tests/application/test_build_verify_handler.py`, reusing each file's existing construction
  helpers and passing `measurements=InMemoryMeasurements()` (`tests/fakes/measurement.py`).

## Acceptance criteria
- [ ] A `build.implement` job whose engine completes records one `LOOP` measurement named after
      the engine, scoped to the job, with outcome `ok`.
- [ ] A `build.verify` job whose reviewer reports a capacity rejection records a `LOOP`
      measurement with outcome `rejected`, and the handler still returns its `Defer`.
- [ ] `build_full_worker` passes `measurements=resources.measurements` to both handlers: an AST
      test finds the keyword on both calls inside `build_full_worker`.
- [ ] Every existing test in both handler test files passes unchanged; 100% branch coverage of
      `src/vibey/application/`.

## Tests to write first (TDD)
- `tests/application/test_build_implement_handler.py`:
  `test_a_completed_implement_run_is_measured`
- `tests/application/test_build_verify_handler.py`:
  `test_a_rejected_verify_run_is_measured_rejected`
- `tests/test_bootstrap.py` (append; no database):
  `test_build_full_worker_measures_both_build_handlers` — parse `src/vibey/bootstrap.py` with
  `ast`, find the `FunctionDef` `build_full_worker`, and assert both the `BuildImplementHandler`
  and the `BuildVerifyHandler` `Call` nodes have a `measurements` keyword whose value is the
  attribute `resources.measurements`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/application/test_build_implement_handler.py tests/application/test_build_verify_handler.py tests/application/test_build_engine_run.py tests/test_bootstrap.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The meter itself (`gap-measure-engine-runs-1`); DESIGN/DECOMPOSE model calls
  (`gap-measure-models-1`); conformance probes.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): the BUILD handlers pass the composed measurement port to every engine run`. Do not push.

## Lane card
- **Depends on:** `gap-measure-engine-runs-1`, `gap-measure-ledger-sink`.
- **Shares a file with:** `bootstrap.py` (see `gap-measure-ledger-sink`); rebase and keep others' code.
- **Must keep passing unchanged:** every existing test in the two handler files, `tests/system/`
  and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
