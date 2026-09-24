## Title
refactor(bootstrap)!: build_app composes over a resources factory, AppResources is typed by ports, and tests open an in-memory app

## Why
`build_app` (`src/vibey/bootstrap.py:693-962`) hard-codes
`asyncpg.create_pool(url or database_url(), ...)` (`:700`). Every piece that needs the
database is built from that pool inline: projects, ledger, jobs, gates, engine health,
rotation cursors, handoffs, the integration lock and (after R02) the wakeup.
`AppResources` (`:133-171`) is typed with those concrete Postgres classes.

As a result:
- every CLI, TUI, operator and system test that goes through `build_app` needs PostgreSQL:
  `tests/cli/test_operational_commands.py` (124 tests), `test_main_integration.py`,
  `test_ledger_search_cli.py`, `test_deploy_cli.py`, `test_sovereign_provider_options.py`,
  `tests/tui/test_dashboard.py`, `tests/system/test_full_worker_faked.py`,
  `tests/infrastructure/test_operator_handlers.py` and `test_cluster_preflight.py`;
- the tests that check `build_app`'s own wiring patch `asyncpg.create_pool`,
  `vibey.bootstrap.PostgresMigrator` and `vibey.bootstrap.database_url`
  (`tests/infrastructure/test_sovereign_surfaces.py:630-720`, `tests/test_bootstrap.py:79-114`);
- `LedgerSearchCommand` reaches into `resources.ledger._pool` (`cli/ledger_search.py:198-199`).

The in-memory families now exist. This lane gives `build_app` a declared seam for its
persistence. Tests then run the **real** composition (surfaces, services, views, engine
adapters) over fakes.

## Required behaviour
1. **Ports on `AppResources`.** Retype every field that holds a Postgres class to its port:
   - `projects: ProjectRepository`, `jobs: JobRepository`, `gates: HumanGateRepository`;
   - `ledger: LedgerRepositoryInterface`;
   - `design_ledger: DesignLedger`, `build_ledger: BuildLedger`, `review_ledger: PhaseLedger`,
     `deploy_review_ledger: PhaseLedger`;
   - `design_specs: DesignSpecRepository`, `visual_inventories: VisualInventoryRepository`;
   - `engine_health_repo: EngineHealthRepository`, `rotation_cursors: RotationCursorRepository`;
   - `handoffs: HandoffStore`, `integration_lock: IntegrationLock | None`.
   Add `ledger_search: LedgerSearch`, built from `PostgresLedgerSearchRepository(pool)` in
   production. `cli/ledger_search.py:198-199` then uses `resources.ledger_search`.
   Run mypy. For each error, either call a method the port declares, or, when production code
   genuinely needs a method the port lacks (for example `HumanGateRepository.get`, which
   Postgres has at `human_gate_repository.py:88`), add it to the port. The shared fake
   already supports it. List every port change in the commit body. Mirror the types in
   `bootstrap_interface.py`'s `AppResourcesInterface`.
2. **`PersistenceInterface` and `ResourcesFactoryInterface`** go in `bootstrap_interface.py`:
   - `PersistenceInterface` is a read-only bundle: `projects`, `ledger`, `jobs`, `gates`,
     `engine_health_repo`, `rotation_cursors`, `handoffs`, `integration_lock`, `wakeup`,
     `ledger_search`;
   - `ResourcesFactoryInterface.open(self, url: str | None, *, notifications: NotificationSink) -> AbstractAsyncContextManager[PersistenceInterface]`.
3. **`class PostgresResourcesFactory`** in `bootstrap.py` moves `:697-712`, plus the pool-backed
   constructions, out of `build_app` unchanged:
   - the migrator read;
   - `create_pool`, through an injected `pool_factory=asyncpg.create_pool`;
   - the version floor (`UnsupportedPostgresVersion`);
   - the migrations;
   - closing the pool on exit.
   `build_app(*, url=None, config=None, resources_factory: ResourcesFactoryInterface | None = None)`
   uses `PostgresResourcesFactory()` by default, and composes everything else exactly as
   today over `persistence.<field>`.
4. **`tests/fakes/app.py`**:
   - `class InMemoryResourcesFactory` (`ResourcesFactoryInterface`) builds one
     `InMemoryPersistence` from the shared fakes. They are wired to one another:
     - `InMemoryQueueStore` shared by `FakeJobRepository` and `FakeHumanGateRepository`, and
       notifying an `InMemoryJobReadyNotifier`;
     - `InMemoryLedger`, and `InMemoryProjectRepository(ledger=...)` over it;
     - `FakeEngineHealthRepository`, `FakeRotationCursorRepository`, `InMemoryHandoffStore`;
     - `InMemoryIntegrationLock`, `InMemoryJobWakeupOpener`, `InMemoryLedgerSearch(ledger)`.
     `open` refuses a `url` that is not `None` and does not start with `memory:`. The last
     persistence it built is `factory.persistence`, for seeding and assertions.
   - `class InMemoryApp` holds `factory` and `config`:
     - `open_app()` returns `build_app(url="memory://", config=self.config, resources_factory=self.factory)`;
     - `composition()` returns `CliComposition(open_app=self.open_app)` (`fakes-job-wakeup`).
   - Register `ResourcesFactoryInterface → InMemoryResourcesFactory()`, and add it to `DRIVER_SEAMS`.
5. **Switch the wiring tests.**
   - `tests/infrastructure/test_sovereign_surfaces.py`'s `build_app` tests (`test_build_app_defaults_to_in_memory_surfaces`,
     `test_build_app_wires_concrete_adapters_from_config`) use `InMemoryApp`. Their four
     `patch(...)`s go.
   - `tests/test_bootstrap.py:79-114` tests `PostgresResourcesFactory(pool_factory=...)`
     directly with its in-test `Pool` class, and the `monkeypatch.setattr` goes.
   - Add `test_build_app_over_the_in_memory_factory_yields_a_working_app`: create a project,
     enqueue a job, claim it, and search the ledger, all through `resources`.
6. **Tests that read concrete Postgres attributes** (`resources.ledger._pool`,
   `PostgresEngineHealthRepository(resources.ledger._pool)`) are not in scope. The CLI lanes
   fix them. Leave them compiling: they are not type-checked.

## Where to change
- `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`, `src/vibey/cli/ledger_search.py:198-199`,
  and any port file that must gain a method (behaviour 1).
- New `tests/fakes/app.py`, `tests/fakes/test_fake_app.py`.
- `tests/fakes/registry.py`, `tests/meta/patching_baseline.json`,
  `tests/infrastructure/test_sovereign_surfaces.py` (the `build_app` tests), `tests/test_bootstrap.py`.

## Acceptance criteria
- [ ] `grep -n "asyncpg.create_pool" src/vibey/bootstrap.py` shows only `PostgresResourcesFactory`'s default.
- [ ] `grep -n "_pool" src/vibey/cli/*.py` prints nothing.
- [ ] `uv run mypy --strict src/vibey` passes, and every production call site is unchanged in behaviour (the full suite with PostgreSQL passes).
- [ ] `test_build_app_over_the_in_memory_factory_yields_a_working_app` passes with PostgreSQL stopped.
- [ ] 100% `cli/` coverage. `bootstrap.py` sits outside the layer gates, but its new code is tested.

## Tests to write first (TDD)
`tests/fakes/test_fake_app.py`:
- `test_in_memory_factory_wires_one_queue_and_one_ledger`
- `test_answering_a_gate_wakes_a_waiter_through_the_wired_notifier`
- `test_in_memory_factory_refuses_a_real_url`
- `test_build_app_over_the_in_memory_factory_yields_a_working_app`

`tests/test_bootstrap.py`:
- `test_postgres_factory_rejects_a_server_below_the_floor_and_closes_the_pool`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/fakes tests/meta tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Moving the CLI, TUI, operator and system tests onto `InMemoryApp` (`fakes-cli-*`,
  `fakes-tui-system`, `fakes-cluster-preflight`).
- R17's queue-backend selection. When it has landed, the factory is where the backend is
  chosen. Rebase, and keep R17's selection inside `PostgresResourcesFactory` or its successor.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally as `refactor(bootstrap)!: …`, with a `BREAKING CHANGE:` footer
saying that `AppResources` fields are now typed by ports.

## Lane card
- **Depends on:** `fakes-ledger-publication`, `fakes-build`, `fakes-review-visual`,
  `fakes-deploy`, `fakes-job-wakeup`, `fakes-observability`. Queue, engines, projects,
  ledger and design come with them.
- **Files touched:** see *Where to change*.
- **Shares a file with:** `src/vibey/bootstrap.py` and `bootstrap_interface.py`
  (R02 → T15 → R17 → T25 → R27 → R28 → T26, and this lane). Rebase on whichever has landed,
  and keep their additions inside the factory or the composition as they belong.
- **Must keep passing unchanged:** the whole suite with PostgreSQL, and the protected tests.
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
