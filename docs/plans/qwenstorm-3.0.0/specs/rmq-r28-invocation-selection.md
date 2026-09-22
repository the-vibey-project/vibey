## Title
feat(engines): the composition root selects subprocess or service invocation

## Why
ADR-0044 §13: `[engines] invocation` chooses how every engine run is made, in one
place. The candidates are:

- the BUILD adapters (`bootstrap.py:736-738`);
- the local-engine adapters (`local_engines.py:143-148`);
- the DESIGN and DECOMPOSE executors the CLI builds (`cli/main.py:428`, `:455`,
  `:1580`, `:1619`).

`subprocess` stays byte-identical. `service` publishes to loop services. Conformance
in service mode needs a worktree the service can reach.

## Required behaviour
1. There is a new `EngineAdapterFactoryInterface`, and two implementations:
   - `SubprocessAdapterFactory` builds `LoopProcessAdapter(descriptor, env_overlay=...)`,
     which is today's behaviour;
   - `ServiceAdapterFactory(client, clock, run_queue_wait, deadline)` builds
     `LoopServiceAdapter`.
2. `LocalEngineSettings.adapter(...)` takes an optional
   `factory: EngineAdapterFactoryInterface = SubprocessAdapterFactory()`, and uses it in
   place of the hard-coded `LoopProcessAdapter` (`local_engines.py:143-148`).
3. `build_app` reads the invocation mode: `VIBEY_ENGINE_INVOCATION` first, then
   `config.engines.invocation`, then `subprocess`. In `service` mode it:
   - builds one `LoopServiceClient` (R27's `build_loop_client`), closed in `finally`;
   - builds `engine_adapters` through `ServiceAdapterFactory`;
   - exposes `AppResources.engine_factory` and `AppResources.command_executor_for(engine_id, binary)`,
     which returns `AsyncSubprocessExecutor()` in `subprocess` mode and
     `LoopServiceCommandExecutor` in `service` mode.

   `build_full_worker` passes `resources.engine_factory` to `LocalEngineSettings.adapter`.
4. `cli/main.py` replaces each `AsyncSubprocessExecutor()` at `:428`, `:455`, `:1580`
   and `:1619` with `resources.command_executor_for(...)` for that engine.
5. In `service` mode, `vibey doctor --conformance` defaults its trivial worktree to
   `<loop_services.root>/.vibey-conformance` (near `:1316`).
6. With the defaults, nothing observable changes.

## Where to change
- The files on the card.
- Put the two factories in `src/vibey/infrastructure/engines/adapter_factory.py`, with
  their interface.

## Acceptance criteria
- [ ] With the default mode, every existing CLI and system test passes unchanged.
- [ ] `VIBEY_ENGINE_INVOCATION=service` with a URL yields `LoopServiceAdapter`s, including for local engines, and service-backed executors in the CLI paths.
- [ ] The conformance worktree default follows the root.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/engines/test_adapter_factory.py`:
  - `test_subprocess_factory_builds_loop_process_adapter`
  - `test_service_factory_builds_loop_service_adapter`
- `tests/infrastructure/engines/test_local_engines.py`: `test_local_adapters_use_the_injected_factory`
- `tests/test_bootstrap.py`:
  - `test_default_invocation_is_subprocess`
  - `test_service_invocation_composes_service_adapters_and_executors`
- `tests/cli/test_operational_commands.py`: `test_conformance_worktree_follows_the_loop_service_root_in_service_mode`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/engines tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Flipping the default (R34).
- The chart (R30).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.

---

## Lane card
- **Depends on:** R01, R25, R26, R27.
- **Wave:** 8.
- **Files touched:**
  - `src/vibey/bootstrap.py`
  - `src/vibey/infrastructure/engines/local_engines.py`
  - `src/vibey/cli/main.py` (executor construction at `:428`, `:455`, `:1580`, `:1619`; conformance worktree near `:1316`)
  - `tests/test_bootstrap.py` (new tests)
  - `tests/infrastructure/engines/test_local_engines.py` (new tests)
  - `tests/cli/test_operational_commands.py` (new tests)
- **Parallel-safe with:** R30. It precedes R33 in the `cli/main.py` chain.
- **Must keep passing unchanged:**
  - every test that patches `LoopProcessAdapter.preflight` (`tests/cli/test_operational_commands.py:942-1968`, `tests/cli/test_sovereign_provider_options.py:146`); they run on the default `subprocess` mode
  - `tests/system/*`
  - `tests/live/**`
  - `tests/infrastructure/engines/test_local_engines.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Standing constraints for every RabbitMQ lane
- **Protected tests are never edited:** `tests/domain/test_noloss*.py`,
  `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
  `tests/system/test_delivery_stage_set.py`, `tests/live/**` (`.vibey-gh.toml:78-85`,
  `.github/CODEOWNERS`). They must keep passing.
- **The first line of every new source file** is the provenance comment, copied
  byte-for-byte from line 1 of a sibling file (`vibey-gh check` compares it exactly).
- **No lane needs a running RabbitMQ.** Unit tests use
  `vibey_bootstrap.amqp.memory.InMemoryAmqpClient` (lane R04). Tests against a real
  broker are marked `integration` and skip unless `VIBEY_TEST_AMQP_URL` is set.
- **SQL runs on PostgreSQL 14:** no `MERGE`, no PostgreSQL 15+ syntax. The 14–18 matrix
  runs `tests/infrastructure/db`.
- **Defaults stay today's until R34:** `queue.backend = "postgres"` and
  `engines.invocation = "subprocess"`.

---
