## Title
test(meta): a meta test fails when a loop, surface, sampler, sink, harness or delivery command goes unmeasured

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`): "Nothing runs unmeasured; a
component that cannot report its measurements is incomplete." The `gap-measure-*` lanes wire a
measurement into each kind of component one at a time. Nothing stops the next surface, sampler
or engine call site from arriving unwired, and 9.c (`:351`) says a claim of completion is not
evidence. This lane makes 8.g mechanical, the way `tests/domain/test_domain_purity.py` makes
domain purity mechanical: static AST checks over the tree, no database, no import of the
composition's runtime.

## Required behaviour
New `tests/meta/test_everything_is_measured.py`. Module-level test functions, with the reason
comment of `tests/meta/test_import_contracts_bind.py:31-32` ("pytest collects `test_*`
functions, and ADR-0016's class rule is about production code"). Paths are resolved from the
repository root (`Path(__file__).resolve().parents[2]`). Every failure message names the file,
the function and what is missing, and says "8.g: nothing runs unmeasured".
1. **Every surface.** In `src/vibey/bootstrap.py`, the annotations of `class AppResources`'s
   fields whose type name ends in `Port`, except `MeasurementPort`, are the surface fields. In
   `build_app`'s `AppResources(` call, each surface field's keyword is a `Call` to
   `surfaces.wrap` whose first argument is the field name as a string literal. A new surface
   field that is not wrapped fails.
2. **The composed port.** The same call passes `measurements=` (a `Name`), and `build_app`
   builds it from `LedgerMeasurementSink(` (and `MeasurementFanOut(` beside
   `FamilyTelemetryMeasurementSink(`).
3. **Every loop.** Every `Call` to `run_and_record` in `src/vibey/application/**/*.py` passes a
   `measurements` keyword; `build_full_worker` passes `measurements=resources.measurements` to
   `BuildImplementHandler(` and `BuildVerifyHandler(`. Every `Call` whose function is an
   attribute named `tail` in `src/vibey/application/**/*.py` is in `build_engine_run.py` or in
   `conformance.py` — the only exemption, with the reason in a module constant
   `UNMEASURED = {"src/vibey/application/conformance.py": "a doctor probe runs no job; its
   verdict is recorded as engine health"}`.
4. **Every model call.** Every `OllamaChatClient.from_environment(` call in
   `src/vibey/cli/main.py` passes `transport=`, and every `OllamaChatClient(` constructed
   anywhere under `src/vibey/cli/` or `src/vibey/bootstrap.py` passes `transport=`.
5. **Every sampler is hosted, every sink is composed.** Import every module of
   `vibey.infrastructure.measure` (`pkgutil.iter_modules`); for each class defined there (its
   `__module__` is that module) with an async `record` (`inspect.iscoroutinefunction`), or with
   an async `collect` and a `name`, the class's name occurs in the source text of
   `src/vibey/bootstrap.py` or `src/vibey/cli/main.py`. Today that is `LedgerMeasurementSink`,
   `FamilyTelemetryMeasurementSink`, `JsonlMeasurementSink`, `JobQueueSampler`, `SurfaceMeter`
   and `OllamaResidencySampler`; a new `RabbitMqQueueSampler` is covered as soon as it exists.
6. **The ticker is hosted.** Inside `worker` in `src/vibey/cli/main.py` there is a
   `MeasurementTicker(` call and an `asyncio.create_task(` whose argument is a `.run(` call.
7. **The harness is measured.** `TestHarnessComposition.instance` in `src/vibey/bootstrap.py`
   returns a `MeasuringHarnessInstance(` call.
8. **The delivery commands are measured.** In `src/vibey_tools/gh/vibey_gh/cli.py`, `main`
   branches on `MEASURED_COMMANDS` before `args.func(args)`, and
   `vibey_gh.command_meter.MEASURED_COMMANDS` contains `merge-train`, `local-review`,
   `pr-automation` and `promote`.
9. **The measurement is a known, published kind.** `EventKind.MEASUREMENT_RECORDED` exists and
   `DEFAULT_ALLOWLIST` has an entry for it.
10. A self-test per rule plants a violation in a small source string (as
    `test_domain_purity_check_fails_on_a_planted_violation` does,
    `tests/domain/test_domain_purity.py:95-103`) and asserts the checker function reports it.
    The checkers are small private helper functions in the test module.

## Where to change
- New `tests/meta/test_everything_is_measured.py` only.

## Acceptance criteria
- [ ] The test passes on the tree after the lanes it depends on.
- [ ] Removing `transport=` from one `OllamaChatClient.from_environment(` call, deleting one
      `surfaces.wrap` keyword, or removing `measurements=` from one `run_and_record` call makes
      it fail naming the site. Check each by hand, then revert.
- [ ] Every planted-violation self-test passes.

## Tests to write first (TDD)
`tests/meta/test_everything_is_measured.py`:
- `test_every_surface_port_is_wrapped`
- `test_the_process_has_one_composed_measurement_port`
- `test_every_engine_run_is_measured`
- `test_only_conformance_tails_an_engine_unmeasured`
- `test_every_local_model_client_is_measured`
- `test_every_sampler_and_sink_is_composed`
- `test_the_worker_hosts_the_ticker`
- `test_the_test_harness_is_measured`
- `test_vibey_gh_measures_its_delivery_commands`
- `test_measurement_is_a_known_published_kind`
- `test_each_checker_catches_a_planted_violation` (parametrized over the checkers)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Any production change: a rule that fails means a `gap-measure-*` lane is incomplete; say
  which in the verdict instead of fixing it here.
- The loop services and surface lane hosts of ADR-0046/0047: their lanes add their own rule to
  this file when they land (append a test; never loosen one).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `test(meta): a meta test fails when a loop, surface, sampler, sink, harness or delivery command goes unmeasured`. Do not push.

## Lane card
- **Depends on:** `gap-measure-otel-sink`, `gap-measure-engine-runs-2`, `gap-measure-queue-sampler`,
  `gap-measure-surfaces-2`, `gap-measure-models-1`, `gap-measure-models-2`,
  `gap-measure-test-runs`, `gap-measure-gh-2`, `gap-measure-cli`.
- **Must keep passing unchanged:** every other test under `tests/meta/`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
