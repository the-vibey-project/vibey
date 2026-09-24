## Title
feat(engines): engine sessions carry the test-harness route, so a model's pytest is queued without it knowing

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:274-276`): "a storm lane … put[s]
[its] run on the queue". Draft ADR-0045 §10 does that transparently: the pytest plugin reads
`VIBEY_HARNESS_ROUTE` from its environment, so every engine vibey launches carries it:
- BUILD sessions, built as subprocess adapters (after rmq-r28, by `SubprocessAdapterFactory`, which
  harness-T26b taught a `routing_overlay`);
- local engines, which after rmq-r28 get their adapter from the same factory
  (`resources.engine_factory`);
- runs inside a loop service (ADR-0044 §13, rmq-r27's `build_loop_service`), whose runners inherit
  the environment overlay it builds from `LocalEndpointEnvironment(environ).overlay_for(engine_id)`.

This lane composes harness-T26a's overlay once in the composition root and passes it to both
places. With the default `[test_harness] route_engines = "off"`, every environment is
byte-identical to today's; harness-T28 turns it on.

## Required behaviour
In `src/vibey/bootstrap.py` (find the sites with
`grep -n "SubprocessAdapterFactory\|build_loop_service\|env_overlay\|overlay_for" src/vibey/bootstrap.py`):
1. Build `routing = HarnessRoutingEnvironment(TestHarnessSettings.from_sources(config, environ)).overlay()`
   once where the engine factory is composed, using the same `config` and environment that
   composition already reads.
2. Pass it as `SubprocessAdapterFactory(routing_overlay=routing)` wherever the composition builds the
   factory (the one `build_full_worker` passes to `LocalEngineSettings.adapter` as `resources.engine_factory`).
3. In `build_loop_service` (rmq-r27), merge it **under** the endpoint overlay:
   `{**routing, **LocalEndpointEnvironment(environ).overlay_for(engine_id)}`.
4. With `route_engines = "off"`, `routing` is `{}` and nothing observable changes.

## Where to change
- `src/vibey/bootstrap.py` (with `edit_file`; the file is over 900 lines).
- `tests/test_bootstrap.py` (tests appended; imports into its import block).

## Acceptance criteria
- [ ] With `[test_harness] route_engines = "queue"`, a composed subprocess adapter's launcher environment (rmq-r20's `EngineProcessLauncher.environment()`) contains `VIBEY_HARNESS_ROUTE=queue` and `VIBEY_HARNESS_WAIT_SECONDS=110`, for a paid and for a local engine.
- [ ] `build_loop_service`'s runner environment contains both variables, and an endpoint key of the same name would win.
- [ ] With the default, the existing engine and system tests pass unchanged.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Appended to `tests/test_bootstrap.py` (configs from `load_config_from_string` with a `[test_harness]`
table; environments are dicts with `HOME` under `tmp_path`; no engine is spawned). Compose the app
with `InMemoryApp` (`tests/fakes/app.py`, lane fakes-bootstrap-seam), which calls
`build_app(url="memory://", config=..., resources_factory=...)`, so no database is opened:
- `test_engines_carry_the_route_when_configured`
- `test_loop_service_runners_carry_the_route`
- `test_the_default_route_changes_no_engine_environment`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/test_harness tests/test_bootstrap.py tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Changing the default (harness-T28). Adopter projects without vibey in their venv (ADR-0045 names that a follow-up).
- The storm driver (`qwenlane.py`, outside the repository): exporting `VIBEY_HARNESS_ROUTE` for tenant-directory runs there is an operator step (ADR-0045 "Where the drafted rule conflicts" item 6).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T26a-harness-routing-environment, harness-T26b-adapter-factory-routing-overlay, rmq-r27-loop-service-cli, rmq-r28-invocation-selection, fakes-bootstrap-seam (`InMemoryApp`).
- **Files touched:** `src/vibey/bootstrap.py`, `tests/test_bootstrap.py`.
- **Shares a file with:** `bootstrap.py` (after rmq-r28, the end of the ADR-0044 chain; harness-T15a and T25b edit `TestHarnessComposition` in the same file, and this lane touches only the engine composition).
- **Must keep passing unchanged:** `tests/infrastructure/engines/*`, `tests/system/*`, `tests/live/**` (protected), every rmq-r27 and rmq-r28 test, and the protected tests.
- **Registry (amendment A4):** nothing new.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names.
  - Substitute only at declared seams (the composition's injected configuration, environment and factories). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out): no engine CLI is spawned.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
