## Title
feat(bootstrap): SurfaceComposition wires the surface lanes — the transport choice in build_app, one lane client per process, and a lane host per surface

## Why
Draft ADR-0047 §12 (`specs/ADR-surface-lanes.md`) puts "the transport choice in `build_app`;
`build_surface_lanes`" in `bootstrap.py`, the sole composition root (CLAUDE.md layer map). The
pieces exist in `vibey.infrastructure.surface_lanes`; this lane composes them:

- the AMQP endpoint comes from R17's `QueueBackendSettings.from_sources(config, environ)` — "the
  AMQP URL, vhost and prefix, with their precedence" (ADR "What exists to build on") — so every
  bus consumer in vibey resolves it the same way (10.e);
- a caller process gets **one** `SurfaceLaneClient` (§6);
- a lane host owns its surface's adapter and credentials, and nothing else does (§1); the cache
  lane serves reads through `PipelinedRedisCache` and its memo when a cache URL is configured
  (§10), and the in-memory cache otherwise ("A lane whose surface has no credentials serves the
  in-memory adapter, and says so at start", §2);
- the lease uses its own connection (`surfaces-amqp-lease-client`).

ADR-0047 lanes S26–S27 (composition).

## Required behaviour
1. **`class SurfaceComposition`** in `src/vibey/bootstrap.py` (the composition root), with
   `SurfaceCompositionInterface` in `src/vibey/bootstrap_interface.py`:
   `__init__(self, *, config: VibeyConfig | None, environ: Mapping[str, str], clock: Clock, logger: Logger, amqp_factory: Callable[[AmqpSettings], AmqpClientInterface] = AmqpClient, leases_factory: Callable[[AmqpSettings], AmqpLeasesInterface] = AmqpLeases, direct: DirectSurfaceFactoryInterface | None = None, caller: SurfaceCallerScopeInterface | None = None)`.
   - `settings = config.surfaces if config else SurfacesConfig()`;
     `endpoint = QueueBackendSettings.from_sources(config, environ)`; `names = SurfaceQueueNames(endpoint.prefix)`;
     `direct` defaults to `DirectSurfaceFactory(config)`; `caller` to
     `ContextVarSurfaceCallerScope(process=ContextVarSurfaceCallerScope.default_process())`.
   - `caller` property.
   - `lane_client(self) -> SurfaceLaneClientInterface`: built once, lazily:
     `amqp = amqp_factory(AmqpSettings(url=endpoint.amqp_url, connection_name="vibey.surfaces.client"))`,
     `SurfaceLaneTopology(amqp, names, settings)`, `SurfaceReplyRouter(amqp, logger=logger)`,
     `SurfaceLaneClient(...)`. Without a URL it raises `SurfaceTransportNotConfigured`.
   - `select(self) -> SelectedSurfaces`: `SurfaceTransportSelector(settings=settings, direct=direct, amqp_url=endpoint.amqp_url, lane_client=self.lane_client, logger=logger).select()`.
   - `host(self, surface: SurfaceName, resources: SurfaceLaneResourcesInterface) -> SurfaceLaneHostInterface`:
     no URL → `SurfaceTransportNotConfigured`. `instance = f"{caller.process}/{surface.value}"`.
     A fresh `amqp = amqp_factory(AmqpSettings(url=…, connection_name=f"vibey.surface.{surface.value}"))`
     and `leases = leases_factory(<same settings>)`. The executor:
     - **cache** with `config.cache.url`: `CacheLaneHandler(cache=PipelinedRedisCache(url=config.cache.url, timeout=settings.adapter_timeout_seconds), settings=settings, clock=clock)`, backend `"PipelinedRedisCache"`;
     - otherwise `SurfaceOperationHandler(adapter=direct.build(surface), settings=settings, clock=clock)`, backend `direct.backend_name(surface)`.
     For a surface with a `GUARDED` operation, `guarded = SurfaceGuardedExecutor(operations=resources.surface_operations, handler=<that handler>, instance=instance)`.
     Then `SurfaceLedgerRecorder(ledger=resources.ledger, projects=resources.projects, clock=clock, logger=logger)`,
     `SurfaceLaneMeter(surface=…, instance=…, logger=logger, clock=clock)`, the
     `SurfaceRequestDispatcher`, the `SurfaceDeadLetterReconciler` over
     `resources.surface_dead_letters` and `resources.surface_operations`, and the
     `SurfaceLaneHost`. Remember every AMQP client and lease holder made.
   - `async aclose(self) -> None`: closes the lane client, every AMQP client and every lease
     holder it made (ignoring close errors); idempotent.
2. **`SurfaceLaneResourcesInterface`** (`bootstrap_interface.py`): a `@runtime_checkable`
   Protocol with read-only `ledger`, `projects`, `surface_operations`, `surface_dead_letters`.
   `AppResources` satisfies it (lane `surfaces-app-records`).
3. **`build_app`**: first move the `resolved_config` resolution (the `vibey.toml`-then-
   environment block, lane `surfaces-env`; it reads only a file and the environment) to the
   start of `build_app`, before the migrator, the pool, or `resources_factory.open(...)` when
   lane `fakes-bootstrap-seam` has landed. Then replace
   `direct = DirectSurfaceFactory(resolved_config).all()` (lane `surfaces-direct-factory`) with
   `surface_composition = SurfaceComposition(config=resolved_config, environ=os.environ, clock=SystemClock(), logger=StructlogAppLogger(component="surfaces"))`
   and `selected = surface_composition.select()`, placed directly after the configuration and
   before any repository, pool or `NotificationService` is built, so a `queue` transport with no
   URL fails the start at once and later wiring can use the selected ports
   (`surfaces-consumer-notifications`). The `yield`
   passes the twelve ports from `selected`; `AppResources` gains, with defaults, at the end:
   `surface_client: SurfaceLaneClientInterface | None = None` and
   `surface_caller: SurfaceCallerScopeInterface | None = None`, passed as
   `selected.lane_client` and `surface_composition.caller`. The `finally` awaits
   `surface_composition.aclose()`. `AppResourcesInterface` declares both new fields.
4. With the default `direct` transport nothing observable changes.

## Where to change
- `src/vibey/bootstrap.py` (the class, `build_app`, `AppResources`), `src/vibey/bootstrap_interface.py`.
- New `tests/test_bootstrap_surfaces.py`.

## Acceptance criteria
- [ ] Default config and empty environment: `select()` is `direct` and in memory; no AMQP client is ever built (`amqp_factory` records no call).
- [ ] `environ={"VIBEY_SURFACES_TRANSPORT": "queue"}` with no URL: `build_app` raises `SurfaceTransportNotConfigured` before yielding.
- [ ] With `VIBEY_SURFACES_TRANSPORT=queue` and `VIBEY_BUS_AMQP_URL=amqp://u:p@h:5672/`, the selected ports are `Queued*` over one client whose AMQP factory was called once with `connection_name="vibey.surfaces.client"`; the bus is direct; the prefix is `VIBEY_BUS_PREFIX`'s.
- [ ] End to end with no service: a `SurfaceComposition` given `amqp_factory` and `leases_factory` returning one shared `InMemoryAmqpClient` and `InMemoryAmqpLeases`, and `InMemoryApp` resources, runs `host(SurfaceName.TRACKER, resources)` as a task; `selected.tracker.create_ticket("t", "d")` returns an id from `InMemoryTracker`; stopping the host returns 0.
- [ ] The cache host uses `PipelinedRedisCache` when `[cache] url` is set, and names that backend at start.
- [ ] `aclose()` closes everything it made, twice safely.
- [ ] `mypy --strict src/vibey` clean; `tests/test_bootstrap.py`, `tests/cli/*` and `tests/infrastructure/test_sovereign_surfaces.py` pass unchanged.

## Tests to write first (TDD)
`tests/test_bootstrap_surfaces.py` (no service; injected factories, `InMemoryApp` from `tests/fakes/app.py`, `FakeClock`, `RecordingLogger`):
- `test_direct_by_default_builds_no_amqp_client`
- `test_queue_without_a_url_fails_the_start`
- `test_queue_selects_queued_ports_over_one_client`
- `test_a_host_serves_a_queued_call_end_to_end`
- `test_the_cache_host_pipelines_when_a_cache_url_is_set`
- `test_aclose_closes_everything_once`
- `test_composition_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/test_bootstrap_surfaces.py tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/test_sovereign_surfaces.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The commands (`surfaces-cli-serve-ping`, `surfaces-cli-dead-letters`); the default flip
  (`surfaces-default-flip`); hosting lanes inside `vibey worker` (named by the ADR as a possible
  later convenience, not this record). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md
  and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit
  locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-transport-selection`, `surfaces-lane-host`, `surfaces-app-records`, `surfaces-config-env`, `surfaces-amqp-lease-client`, `rmq-r17-queue-backend-selection` (`QueueBackendSettings`), `split-351-2-amqp-client` (`AmqpClient`).
- **Shares a file with:** `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py` (the chain in `surfaces-app-records`'s card). Keep everything earlier lanes added.
- **Must keep passing unchanged:** `tests/test_bootstrap.py`, `tests/cli/*`, `tests/system/*`, `tests/infrastructure/test_sovereign_surfaces.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file. `bootstrap.py` is long: `edit_file` only.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol beside it (`bootstrap_interface.py` for the composition root).
  - Substitute only at a declared seam (`amqp_factory=`, `leases_factory=`, `environ=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service; `[surfaces] transport` stays `direct` by default.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
