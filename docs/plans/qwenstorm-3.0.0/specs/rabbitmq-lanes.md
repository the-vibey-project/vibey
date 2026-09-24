# RabbitMQ queue and loop services: implementation lanes (R01–R35)

Design: `specs/ADR-rabbitmq-queue.md` (ADR-0044 draft). Evidence cutoff: `develop` at
`d47c196d` (read in the storm worktree `changelog-2.1.0`, since lost to the 2026-09-24 reboot; the commit is the evidence), read 2026-09-22.
Every `file:line` below is at that commit.

## How to file these

This file holds 34 implementation lanes (R01–R34) and one docs-wave lane (R35). Each
lane starts at a `# Lane Rnn` heading, and the lanes are separated by `---`. Before you
run `file-issue.py`, split the file at those headings into
`specs/rabbitmq-Rnn-<slug>.md`, one lane per file. The script reads the first
`## Title`, so each lane must be its own file.

Each lane is the full template (`SPEC-TEMPLATE.md`), in order. It is preceded by a
**lane card**, which gives:

- the lanes it depends on;
- its wave;
- the files it touches, so you can tell which lanes can run in parallel;
- the existing tests that must keep passing **unchanged**.

The card is the same kind of preamble the opencodeloop-parity spec carries.

## Order, waves and parallel safety

A lane can start once every lane it depends on has merged. Lanes in the same wave
touch disjoint files, except where the table says otherwise.

| lane | slug | depends on | wave | files touched (short form) |
|---|---|---|---|---|
| R01 | queue-config | — | 1 | `domain/config.py`, `domain/interfaces/config_interface.py`, `infrastructure/config_loader.py` |
| R02 | wakeup-composition | — | 1 | `bootstrap.py`, `bootstrap_interface.py`, `cli/main.py` |
| R03 | amqp-dependency | — | 1 | `pyproject.toml`, `src/vibey_tools/bootstrap/pyproject.toml`, `uv.lock`, `.importlinter` |
| R05 | async-outbox | — | 1 | `vibey_bootstrap/db/outbox.py` |
| R06 | job-dispatch-envelope | — | 1 | `domain/job_dispatch.py` (+ interface) |
| R08 | dispatch-migration | — | 1 | `migrations/0014_job_dispatch.sql`, `infrastructure/db/orm_models.py` |
| R09 | reap-bound | — | 1 | `infrastructure/db/job_repository.py` |
| R19 | run-protocol | — | 1 | `domain/run_protocol.py` (+ interface) |
| R20 | run-dir-extraction | — | 1 | `infrastructure/engines/{run_dir,process_launcher,loop_process_adapter}.py` |
| R04 | bootstrap-amqp | R03 | 2 | `vibey_bootstrap/amqp/**` |
| R07 | dispatch-miss-policy | R06 | 2 | `domain/dispatch_policy.py` (+ interface) |
| R10 | dispatch-records-enqueue | R05 R06 R08 | 2 | `infrastructure/db/dispatch_records.py` (+ interface) |
| R21 | local-run-executor | R19 R20 | 2 | `infrastructure/loop_service/{local_run_executor,result_store}.py`, `.importlinter` |
| R29 | chart-broker-core | R01 | 2 | `deploy/helm/vibey/{templates/broker.yaml,templates/surfaces.yaml,templates/worker.yaml,values.yaml}`, goldens |
| R11 | dispatch-records-settle | R07 R09 R10 | 3 | `infrastructure/db/dispatch_records.py` |
| R12 | queue-topology | R04 R06 | 3 | `infrastructure/queue/rabbitmq_topology.py`, `.importlinter`, `tests/infrastructure/queue/conftest.py` |
| R15 | gate-redispatch | R10 | 3 | `infrastructure/db/human_gate_repository.py` |
| R22 | loop-service-host | R04 R21 | 3 | `infrastructure/loop_service/host.py` |
| R24 | loop-service-client | R04 R19 | 3 | `infrastructure/loop_service/client.py` |
| R13 | dispatch-relay | R05 R08 R10 R12 | 4 | `infrastructure/queue/dispatch_relay.py` |
| R14 | project-deliveries | R12 | 4 | `infrastructure/queue/{project_deliveries,rabbitmq_wakeup}.py` |
| R23 | loop-service-control | R22 | 4 | `infrastructure/loop_service/{control,host}.py` |
| R25 | loop-service-adapter | R20 R24 | 4 | `infrastructure/loop_service/adapter.py`, `application/{dto,worker,build_implement_handler}.py` |
| R16 | rabbitmq-job-repository | R11 R13 R14 R15 | 5 | `infrastructure/queue/rabbitmq_job_repository.py` |
| R26 | loop-service-executor | R24 R25 | 5 | `infrastructure/loop_service/command_executor.py` |
| R17 | queue-backend-selection | R01 R02 R16 | 6 | `bootstrap.py`, `bootstrap_interface.py`, `cli/main.py` |
| R18 | queue-contract-suite | R17 | 7 | `tests/contracts/test_job_queue_contract.py`, `tests/infrastructure/queue/test_rabbitmq_chaos.py` |
| R27 | loop-service-cli | R17 R23 R24 R25 | 7 | `cli/loop_service.py`, `cli/main.py`, `bootstrap.py`, `infrastructure/loop_service/residency.py` |
| R28 | invocation-selection | R01 R25 R26 R27 | 8 | `bootstrap.py`, `infrastructure/engines/local_engines.py`, `cli/main.py` |
| R30 | chart-loop-services | R27 R29 | 8 | `templates/loop-services.yaml`, `templates/worker.yaml`, `values.yaml`, goldens |
| R31 | chart-keda-rabbitmq | R29 R30 | 9 | `templates/keda-scaledobject.yaml`, `golden/render.sh`, goldens |
| R33 | install-and-doctor | R28 | 9 | `infrastructure/rabbitmq_local.py`, `cli/main.py` |
| R32 | ci-rabbitmq | R18 R30 R31 | 10 | `.github/workflows/ci.yml` |
| R34 | defaults-flip | R01–R33 | 11 | `domain/config.py`, `values.yaml`, `tests/conftest.py`, goldens |
| R35 | docs-wave | R34 | 12 | `docs/**`, ADRs, `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`, agent trees, `CHANGELOG.md` |

**Serial chains.** These lanes share a hot file, so run each chain strictly in order.
Later lanes rebase on earlier ones.

| hot file | lanes, in order |
|---|---|
| `bootstrap.py` | R02 → R17 → R27 → R28 |
| `cli/main.py` | R02 → R17 → R27 → R28 → R33 |
| `.importlinter` | R03 → R21 → R12 |
| `infrastructure/db/dispatch_records.py` | R10 → R11 |
| `loop_service/host.py` | R22 → R23 |
| chart goldens | R29 → R30 → R31 → R34 |

**In-flight 3.0.0 storm lanes touch the same files.** Rebase on whichever of them
lands first:

- `openstack-client`: `domain/config.py`, `infrastructure/config_loader.py`, `bootstrap.py`, `cli/main.py`;
- `surfaces-env`: `bootstrap.py`, `infrastructure/config_loader.py`, `templates/worker.yaml`;
- `engines-pool` and `engines-provider`: `bootstrap.py`, `cli/main.py`, `values.yaml`;
- `chart-operator-forgejo`: `templates/surfaces.yaml`, `values.yaml`, `golden/render.sh`, the goldens.

## Standing constraints (every lane restates them in its card)

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

# Lane R01 — queue-config

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/config.py`
  - `src/vibey/domain/interfaces/config_interface.py`
  - `src/vibey/infrastructure/config_loader.py`
  - `tests/domain/test_config.py`
  - `tests/infrastructure/test_config_loader.py`
- **Parallel-safe with:** every other wave-1 lane.
- **Must keep passing unchanged:**
  - every existing test in `tests/domain/test_config.py` and `tests/infrastructure/test_config_loader.py`
  - `tests/infrastructure/test_sovereign_surfaces.py`
  - `tests/test_bootstrap.py`
  - `tests/domain/test_domain_purity.py`
  - all protected tests
- **Standing constraints:** see the list above. Keep the provenance line; PostgreSQL 14 SQL; no broker needed; defaults stay `postgres`/`subprocess`.

## Title
feat(config): declare the queue backend, the AMQP endpoint and the engine invocation mode

## Why
ADR-0044 §1, §13 and §14 (draft at `specs/ADR-rabbitmq-queue.md`) make two things
selectable: the job-queue backend (`postgres` or `rabbitmq`) and how vibey invokes a
loop engine (`subprocess` or `service`). Sub-doctrine 12.c
(`src/vibey_tools/gh/docs/doctrines.md:284`) requires every tunable to be a key.

Today `[bus]` has only `url`, `username` and `password`
(`src/vibey/domain/config.py:289-295`, parsed at `:622-626`), which is the
management-HTTP endpoint. There is no AMQP URL, no queue backend, no invocation mode
and no per-engine prefetch. The environment overlay a cluster uses lives at
`src/vibey/infrastructure/config_loader.py:17-58`.

This lane only declares and validates the keys. Nothing reads them yet; lanes R17 and
R28 do.

## Required behaviour
1. `BusConfig` gains three fields:
   - `amqp_url: str | None = None`
   - `vhost: str = "/"`
   - `prefix: str = "vibey"`, which must match `^[a-z][a-z0-9_-]{0,31}$`, else
     `ConfigError("bus.prefix", ...)`
2. A new frozen, slotted dataclass `QueueRabbitMqConfig`:

   | field | default | constraint |
   |---|---|---|
   | `delivery_limit: int` | `20` | 1–1000 |
   | `consumer_timeout_seconds: int` | `21600` | ≥ 60 |
   | `wait_tiers_seconds: tuple[int, ...]` | `(1, 5, 30, 120, 600, 3600)` | non-empty, each ≥ 1, strictly ascending |
   | `reconcile_interval_seconds: int` | `30` | ≥ 1 |
   | `redispatch_after_seconds: int` | `900` | ≥ 60 |
   | `first_claim_wait_seconds: float` | `2.0` | ≥ 0 |

3. A new `QueueConfig(backend: str = "postgres", rabbitmq: QueueRabbitMqConfig =
   QueueRabbitMqConfig())`. `backend` must be `postgres` or `rabbitmq`. It is parsed
   from `[queue]` and `[queue.rabbitmq]`.
4. `EnginesConfig` gains `invocation: str = "subprocess"` (`subprocess` or `service`),
   parsed from `[engines] invocation`.
5. Two new loop-service dataclasses:
   - `LoopServiceConfig`:

     | field | default | constraint |
     |---|---|---|
     | `prefetch: int` | `1` | 1–64 |
     | `run_queue_wait_seconds: int` | `3600` | ≥ 1 |
     | `supersede_grace_seconds: int` | `30` | ≥ 1 |
     | `publish_progress: bool` | `True` | — |

   - `LoopServicesConfig(root: str = "/", engines: Mapping[str, LoopServiceConfig])`.
     `root` must be an absolute path. The engine tables come from
     `[loop_services.<engine_id>]` sub-tables. An engine id not in `KNOWN_ENGINES`
     (`config.py:25-33`) raises `ConfigError("loop_services", ...)`.
     `for_engine(engine_id: str) -> LoopServiceConfig` returns that engine's table, or
     the defaults.
6. `VibeyConfig` (`config.py:319-342`) gains `queue: QueueConfig` and
   `loop_services: LoopServicesConfig`, both defaulted, and `parse_config` (`:652`)
   fills them.
7. `_SURFACE_ENV_VARS` in `config_loader.py` gains these rows, in this order, directly
   after the existing `bus` rows:
   - `("bus", "amqp_url", "VIBEY_BUS_AMQP_URL", str)`
   - `("bus", "vhost", "VIBEY_BUS_VHOST", str)`
   - `("bus", "prefix", "VIBEY_BUS_PREFIX", str)`
   - `("queue", "backend", "VIBEY_QUEUE_BACKEND", str)`
   - `("engines", "invocation", "VIBEY_ENGINE_INVOCATION", str)`
   - `("loop_services", "root", "VIBEY_LOOP_SERVICES_ROOT", str)`

   `_parse_loop_services` treats the string key `root` as the root, and every table key
   as an engine.
8. Every error names its dotted key, the way `_optional` does (`config.py:358-364`).

## Where to change
- `src/vibey/domain/config.py`:
  - Copy the `BusConfig` / `_parse_bus` pattern (`:289-295`, `:622-626`).
  - Add `_parse_queue` and `_parse_loop_services`.
  - Extend `_parse_engines` (`:403`) to read `invocation`.
  - Wire the new fields into `VibeyConfig` and `parse_config`.
- `src/vibey/domain/interfaces/config_interface.py`: add read-only property Protocols
  `QueueConfigInterface`, `QueueRabbitMqConfigInterface`, `LoopServiceConfigInterface`
  and `LoopServicesConfigInterface`. Copy `TelemetryConfigInterface` (`:31`).
- `src/vibey/infrastructure/config_loader.py:17-58`.

## Acceptance criteria
- [ ] `parse_config({"project": {"name": "x"}})` returns backend `postgres`, invocation `subprocess`, `amqp_url` None, prefix `vibey`, and the loop-service defaults.
- [ ] Each invalid value named in behaviours 1–5 raises `ConfigError` naming its key.
- [ ] `VIBEY_QUEUE_BACKEND=rabbitmq` and `VIBEY_BUS_AMQP_URL=amqp://u:p@h:5672/` override a file that says otherwise.
- [ ] `LoopServicesConfig.for_engine("qwenloop")` returns the defaults when no table exists.
- [ ] Every new config value satisfies its interface (`isinstance`).
- [ ] 100% branch coverage on `domain/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/domain/test_config.py`:
  - `test_queue_defaults_to_postgres_and_subprocess`
  - `test_queue_backend_rejects_unknown`
  - `test_wait_tiers_must_ascend`
  - `test_wait_tiers_must_be_non_empty_and_positive`
  - `test_delivery_limit_bounds`
  - `test_consumer_timeout_floor`
  - `test_bus_prefix_pattern`
  - `test_engines_invocation_values`
  - `test_loop_services_rejects_unknown_engine`
  - `test_loop_services_prefetch_bounds`
  - `test_loop_services_root_must_be_absolute`
  - `test_loop_services_for_engine_defaults`
  - `test_new_config_values_satisfy_their_interfaces`
- `tests/infrastructure/test_config_loader.py`:
  - `test_amqp_and_queue_env_overrides_win`
  - `test_empty_amqp_env_value_is_unset`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain/test_config.py tests/infrastructure/test_config_loader.py tests/infrastructure/test_sovereign_surfaces.py tests/test_bootstrap.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Reading these keys at runtime (R17, R28).
- The chart (R29).
- Flipping the defaults (R34).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees; the docs wave (R35) owns them.

Do not push or change remotes. Commit locally with the Title as the subject.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R02 — wakeup-composition

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/bootstrap.py`
  - `src/vibey/bootstrap_interface.py`
  - `src/vibey/cli/main.py`
  - `tests/test_bootstrap.py`
- **Parallel-safe with:** every other wave-1 lane. It is the start of the
  `bootstrap.py` / `cli/main.py` chain.
- **Must keep passing unchanged:**
  - `tests/cli/test_operational_commands.py`, which patches `vibey.infrastructure.db.notifier.PostgresJobReadyNotifier` at `:1255`
  - `tests/cli/test_sovereign_provider_options.py` (the same patch at `:151`)
  - `tests/infrastructure/db/test_notifier.py`
  - `tests/cli/test_main_integration.py`
  - `tests/test_bootstrap.py`
  - `tests/system/test_full_worker_faked.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
refactor(worker): the composition root builds the job-ready wakeup

## Why
ADR-0044 §1 says the composition root is the only place that knows which queue backend
runs. Today the CLI knows:

- `vibey worker` imports and builds `PostgresJobReadyNotifier(database_url())` itself
  (`src/vibey/cli/main.py:1467` and `:1715-1716`);
- `AppResources` types `jobs` as the concrete `PostgresJobRepository`
  (`src/vibey/bootstrap.py:136`).

This lane moves that choice into `bootstrap.py` and changes no behaviour.

## Required behaviour
1. `AppResources.jobs` is annotated as the `JobRepository` Protocol
   (`vibey.application.interfaces.queue`, `:89`). The value is still
   `PostgresJobRepository(pool)` (`bootstrap.py:918`).
2. There is a new class `JobWakeupOpener` in `src/vibey/bootstrap.py`. It is
   constructed with the DSN and has two methods:
   - `async def open(self) -> JobReadyNotifier` does
     `from vibey.infrastructure.db import notifier as db_notifier` **inside the method
     body**, builds `db_notifier.PostgresJobReadyNotifier(self._dsn)`, awaits
     `connect()`, and returns it. The import must be at call time so that the existing
     tests' `patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier")` still
     reaches it.
   - `async def close(self, notifier: JobReadyNotifier) -> None` awaits
     `notifier.close()` when the notifier has one.
3. `AppResources` gains a required field `wakeup: JobWakeupOpenerInterface`, built in
   `build_app` from `url or database_url()`. There is exactly one construction
   (`bootstrap.py:916`).
4. `vibey worker` gets its notifier from `await resources.wakeup.open()` and closes it
   with `await resources.wakeup.close(notifier)` in the existing `finally`
   (`cli/main.py:1756-1760`). The import at `:1467` goes away.
5. Behaviour is unchanged: same channel, same 5 s wait, same output lines.

## Where to change
- `src/vibey/bootstrap.py`: `AppResources` (`:134-171`), `build_app` (`:694-916`).
- `src/vibey/bootstrap_interface.py`:
  - Add `JobWakeupOpenerInterface`, a Protocol with `open` and `close`.
  - Add a `wakeup` property to `AppResourcesInterface`.
  - Follow the style of the existing Protocols in that file.
- `src/vibey/cli/main.py:1467`, `:1715-1716` and the `finally` near `:1756`.

## Acceptance criteria
- [ ] `grep -n PostgresJobReadyNotifier src/vibey/cli/main.py` prints nothing.
- [ ] Both existing CLI tests that patch the notifier class pass without edits.
- [ ] `JobWakeupOpener` satisfies `JobWakeupOpenerInterface`.
- [ ] 100% coverage on `cli/` and `infrastructure/`. `bootstrap.py` sits outside the layer gates, but its new code is still tested.

## Tests to write first (TDD)
- `tests/test_bootstrap.py`:
  - `test_the_wakeup_opener_builds_the_postgres_notifier_at_call_time` (patch the class, assert it was built with the DSN and connected)
  - `test_the_wakeup_opener_closes_what_it_opened`
  - `test_the_wakeup_opener_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/db/test_notifier.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Choosing a backend (R17).
- The RabbitMQ wakeup (R14).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R03 — amqp-dependency

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `pyproject.toml`
  - `src/vibey_tools/bootstrap/pyproject.toml`
  - `uv.lock`
  - `.importlinter`
  - `tests/meta/test_amqp_dependency_declared.py` (new)
- **Parallel-safe with:** every other wave-1 lane. It starts the `.importlinter` chain.
- **Must keep passing unchanged:**
  - `tests/meta/test_import_contracts_bind.py`
  - `tests/meta/test_shipped_trees_are_reachable.py`
  - `tests/meta/test_tools_matrix_covers_every_package.py`
  - `tests/domain/test_domain_purity.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
build(deps): aio-pika is the family's AMQP client

## Why
ADR-0044 §14 and sub-doctrine 10.e (`doctrines.md:246`) apply here: the family is
checked first. `src/vibey_tools/bootstrap` has no AMQP client. Its `servicebus/`
module is Azure Service Bus only. The existing `RabbitMqBusAdapter` uses the
management HTTP API's diagnostics `get` with `ackmode: ack_requeue_false`
(`src/vibey/infrastructure/bus/rabbitmq.py:99-114`), which runs at most once, with no
prefetch and no redelivery.

A queue backend needs a real AMQP 0-9-1 consumer. This is the one third-party
dependency the design adds. The module that uses it arrives in R04. This lane only
declares and locks it.

## Required behaviour
1. The root `pyproject.toml` `[project] dependencies` gains `"aio-pika>=9.5"` under a
   comment line: `# the job-queue and loop-service transport (ADR-0044): AMQP 0-9-1 for RabbitMQ`.
   Put it in the conductor block, after `asyncpg`.
2. `src/vibey_tools/bootstrap/pyproject.toml` gains an extra
   `amqp = ["aio-pika>=9.5"]`, and `"aio-pika>=9.5"` is appended to its `all` extra
   (`:166-181`).
3. `uv lock` is regenerated, and `uv lock --check` passes. Name the newly locked
   package names in the commit body; the expectation is `aio-pika`, `aiormq` and
   `pamqp`, with `yarl`, `multidict`, `propcache` and `idna` already present.
4. `.importlinter` `[importlinter:contract:domain-independence]` `forbidden_modules`
   gains `aio_pika`, `aiormq` and `pamqp`.
5. `uv run pip-audit` passes. If it reports an advisory against a newly locked package,
   **stop and report**. Do not pin around it silently.

## Where to change
- `pyproject.toml:19-50`
- `src/vibey_tools/bootstrap/pyproject.toml` (the extras table near `:120-181`)
- `.importlinter:36-53`
- `uv.lock`, regenerated by `uv lock`, never hand-edited

## Acceptance criteria
- [ ] `uv lock --check` passes.
- [ ] `uv run python -c "import aio_pika"` works.
- [ ] `uv run lint-imports` passes.
- [ ] `tests/meta/test_import_contracts_bind.py` passes.
- [ ] `uv run pip-audit` passes.

## Tests to write first (TDD)
- `tests/meta/test_amqp_dependency_declared.py`:
  - `test_root_distribution_requires_aio_pika`: parse `pyproject.toml` with `tomllib`.
  - `test_bootstrap_amqp_and_all_extras_require_aio_pika`.
  - `test_domain_forbids_the_amqp_client`: read `.importlinter` with `configparser`
    and assert the three names are in the domain contract.

  These are module-level test functions, for the reason `tests/meta/test_adr_counts.py`
  gives.

## Checks the lane must run (all must pass)
    uv lock --check
    uv sync --extra dev
    uv run ruff check . && uv run ruff format --check .
    uv run lint-imports
    uv run pip-audit
    uv run pytest -q -p no:cacheprovider tests/meta tests/domain/test_domain_purity.py

## Out of scope
- Any code that imports `aio_pika` (R04).
- The chart.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R04 — bootstrap-amqp

**Lane card.**

- **Depends on:** R03.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/{__init__,settings,properties,delivery,errors,client,memory}.py` (new)
  - `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/{__init__,client_interface}.py` (new)
  - `src/vibey_tools/bootstrap/test/amqp/{__init__,test_settings,test_memory_client,test_client_unit,test_client_integration}.py` (new)
- **Parallel-safe with:** R07, R10, R21 and R29.
- **Must keep passing unchanged:**
  - the whole vibey-bootstrap suite, `(cd src/vibey_tools/bootstrap && pytest test/ -m "not integration")`
  - the root suite
  - all protected tests
- **Standing constraints:** see the list above.

## Title
feat(bootstrap): vibey_bootstrap.amqp, the family's RabbitMQ client

## Why
Sub-doctrine 10.e: a capability gap is closed by teaching the family, not by writing a
private copy in one consumer.

The family's only consumer machinery is Azure Service Bus
(`vibey_bootstrap/servicebus/consumer_wrapper.py:26-35` and `:53-92`), and it is sync.
Its settle vocabulary is `complete`, `abandon` and `dead_letter`. ADR-0044 §14 puts
the RabbitMQ transport here, under that same vocabulary, so that both vibey's queue
backend and its loop services use one client. The module's docstring carries the
written capability-gap reason.

## Required behaviour
1. **`settings.py`:** `AmqpSettings`, a frozen dataclass:
   - `url: str`, which must start with `amqp://` or `amqps://`, else `ValueError`
   - `connection_name: str = "vibey"`
   - `heartbeat_seconds: int = 60`
   - `publish_timeout_seconds: float = 10.0`
   - `redacted_url() -> str` replaces the password with `***`
2. **`properties.py`:** `AmqpProperties`, a frozen dataclass:
   - `message_id: str | None = None`
   - `correlation_id: str | None = None`
   - `reply_to: str | None = None`
   - `type: str | None = None`
   - `content_type: str = "application/json"`
   - `delivery_mode: int = 2`
   - `priority: int | None = None`
   - `headers: Mapping[str, object] = {}` (use `field(default_factory=dict)`)
3. **`delivery.py`:** `AmqpDelivery`, with these attributes:
   - `body: bytes`
   - `properties: AmqpProperties`
   - `routing_key: str`
   - `redelivered: bool`
   - `delivery_count: int`, read from the `x-delivery-count` header, 0 when absent

   It has three async settle methods, each returning `True` when it settled and
   `False` if the delivery was already settled:
   - `complete()` = `basic.ack`
   - `abandon()` = `basic.nack(requeue=True)`
   - `dead_letter()` = `basic.reject(requeue=False)`

   Each settle calls `vibey_bootstrap.heartbeat.record_message_settled()`.
4. **`errors.py`:** `AmqpError`, `AmqpPublishError(AmqpError)` and
   `AmqpNotConnected(AmqpError)`.
5. **`client.py`:** `AmqpClient(settings, *, connector=aio_pika.connect_robust)`. The
   connector is injected so that unit tests pass a fake, with no patching.
   - `connect()` opens a robust connection with
     `client_properties={"connection_name": ...}` and `heartbeat`, plus one publish
     channel with `publisher_confirms=True`.
   - `close()` closes it.
   - Any other method called before `connect()` connects lazily.
   - `declare_exchange(name, kind)`: `kind` is `direct`, `topic` or `fanout`; durable.
   - `declare_queue(name, *, arguments=None, durable=True, exclusive=False, auto_delete=False) -> str`
     returns the real name. Pass `""` for a server-named queue.
   - `bind(queue, exchange, routing_key)`.
   - `publish(exchange, routing_key, body, properties, *, mandatory=True)` waits for
     the confirm, and raises `AmqpPublishError` on a nack, a return (unroutable while
     mandatory), or a timeout.
   - `consume(queue, *, prefetch, handler) -> str` opens a dedicated channel per
     consumer with `set_qos(prefetch_count=prefetch)`. It calls
     `handler(AmqpDelivery)` for each message, calls
     `vibey_bootstrap.heartbeat.record_consumer_iteration()` per message, and returns
     the consumer tag.
   - `cancel(tag)`.
   - `get(queue) -> AmqpDelivery | None` is `basic.get` without auto-ack.
6. **`memory.py`:** `InMemoryAmqpClient`, which implements the same interface with no
   network:
   - direct routing, topic routing (`*` and `#`) and fanout routing;
   - FIFO queues;
   - push to consumers up to `prefetch` unsettled messages;
   - `abandon` requeues at the head and increments `x-delivery-count`;
   - a queue declared with `x-delivery-limit` dead-letters, to its
     `x-dead-letter-exchange` with the routing key kept, any message whose count would
     exceed the limit;
   - `dead_letter()` routes to the queue's DLX;
   - `simulate_channel_close(tag)` returns every unsettled delivery of that consumer,
     with its count incremented;
   - `expire(queue)` dead-letters every message of a queue declared with
     `x-message-ttl` to its DLX, keeping the routing key. Tests call it instead of
     sleeping;
   - `published` is a list of `(exchange, routing_key, body, properties)` for
     assertions;
   - a mandatory publish that routes nowhere raises `AmqpPublishError`.
7. **`interfaces/client_interface.py`:** `AmqpClientInterface` and
   `AmqpDeliveryInterface`, both `runtime_checkable` Protocols. Mirror the layout of
   `vibey_bootstrap/services/interfaces/`.
8. **`__init__.py`:** exports the public names. Its module docstring states the 10.e
   reason: "The family had no AMQP client; the management HTTP API's `get` is a
   diagnostics endpoint with at-most-once, prefetch-free semantics
   (vibey/infrastructure/bus/rabbitmq.py). ADR-0044 §14."

## Where to change
- The new package under `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/`.
- Copy the `Protocol` + implementation style of `vibey_bootstrap/servicebus/consumer_wrapper.py`.
- aio-pika API: `aio_pika.connect_robust`, `connection.channel(publisher_confirms=True)`,
  `channel.set_qos`, `channel.declare_exchange`, `channel.declare_queue`,
  `queue.bind`, `exchange.publish(aio_pika.Message(...), routing_key, mandatory=True)`,
  `queue.consume`, `message.ack()`, `message.nack(requeue=True)`,
  `message.reject(requeue=False)`, `queue.get(no_ack=False, fail=False)`.

## Acceptance criteria
- [ ] The in-memory client routes, respects prefetch, counts deliveries, dead-letters at the limit, expires TTL queues, and refuses unroutable mandatory publishes.
- [ ] `AmqpClient` works against a fake connector: it declares, publishes with a confirm, consumes with qos, and settles.
- [ ] The integration test passes against a real broker when `VIBEY_TEST_AMQP_URL` is set, and is skipped otherwise.
- [ ] The tenant's static gates pass (mypy, bandit).

## Tests to write first (TDD)
- `test/amqp/test_settings.py`:
  - `test_url_scheme_is_required`
  - `test_redacted_url_hides_the_password`
- `test/amqp/test_memory_client.py`:
  - `test_topic_routing_matches_star_and_hash`
  - `test_prefetch_bounds_unsettled_pushes`
  - `test_abandon_requeues_at_head_and_counts`
  - `test_delivery_limit_dead_letters_with_the_routing_key`
  - `test_channel_close_returns_unsettled_deliveries`
  - `test_expire_moves_ttl_messages_to_the_dlx`
  - `test_unroutable_mandatory_publish_raises`
  - `test_settling_twice_returns_false`
- `test/amqp/test_client_unit.py`: drive `AmqpClient` through a fake connector object
  (no network), asserting it declares, publishes and waits for the confirm, raises on
  a nack, sets qos per consumer, and maps `complete`, `abandon` and `dead_letter` to
  ack, nack and reject.
- `test/amqp/test_client_integration.py` (`@pytest.mark.integration`, skipped without
  `VIBEY_TEST_AMQP_URL`):
  - `test_round_trip_against_a_real_broker`
  - `test_quorum_delivery_limit_dead_letters_after_channel_closes`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/amqp -m "not integration")
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Anything under `src/vibey/`.
- Topology (R12).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R05 — async-outbox

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey_tools/bootstrap/vibey_bootstrap/db/outbox.py`
  - `src/vibey_tools/bootstrap/test/db/test_outbox_async.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `src/vibey_tools/bootstrap/test/db/test_outbox.py` (the sync API must not change)
  - the whole vibey-bootstrap suite
  - all protected tests
- **Standing constraints:** see the list above.

## Title
feat(bootstrap): an async outbox the asyncpg world can share

## Why
ADR-0044 §4 dispatches jobs through a transactional outbox written **inside the same
asyncpg transaction** as the job's state change. vibey's queue is asyncpg
(`src/vibey/infrastructure/db/job_repository.py:49-64`).

The family's outbox (`vibey_bootstrap/db/outbox.py:57-183`) has two gaps:

- it is sync SQLAlchemy only;
- a row a relay claimed as `sending` stays `sending` forever if that relay dies before
  `mark_sent` (`:97-112`, `:147-183`).

Sub-doctrine 10.e says to close the gap in the family's package. The sync API stays
exactly as it is.

## Required behaviour
1. `class OutboxSchema` has one method, `ddl(table: str, *, tracked: bool) -> str`.
   The table name is validated by `_validate_identifier` (`:24-28`).
   - `tracked=False` returns exactly the existing `OUTBOX_DDL` text with the table name
     substituted.
   - `tracked=True` adds a column `claimed_at TIMESTAMPTZ` and a constraint
     `CHECK (status IN ('pending','sending','sent','failed'))`.
2. `class AsyncOutboxExecutor(Protocol)` declares two methods:
   - `async def execute(self, query: str, *args: object) -> str`
   - `async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, object]]`

   `asyncpg.Connection` satisfies it structurally.
3. `class AsyncOutbox(executor, *, table="outbox", track_claims=False)`, using `$n`
   parameters throughout:
   - `enqueue(idempotency_key, payload) -> bool` runs
     `INSERT … ON CONFLICT (idempotency_key) DO NOTHING` and returns `True` when a row
     was inserted.
   - `claim_batch(limit, *, max_attempts=5) -> list[OutboxMessage]` is one statement:
     `UPDATE t SET status='sending'[, claimed_at=now()] WHERE id IN (SELECT id FROM t WHERE status='pending' AND attempt_count < $2 ORDER BY created_at LIMIT $1 FOR UPDATE SKIP LOCKED) RETURNING *`.
     It needs no long transaction.
   - `mark_sent(msg_id)` and `mark_failed(msg_id, error, *, max_attempts=5)` behave as
     the sync methods do (`:114-144`).
   - `reclaim_stale(older_than_seconds: float) -> int` returns `sending` rows whose
     `claimed_at` is older than the cutoff to `pending`. It raises `ValueError` unless
     `track_claims=True`.
4. `class AsyncOutboxDrainer(outbox, sender)`, where `sender` is
   `Callable[[OutboxMessage], Awaitable[None]]`. `drain(limit) -> int` claims a batch
   and sends each row: a success is marked sent, and an exception is marked failed and
   logged, never raised. It returns the count sent.
5. The `outbox.*` counters are bumped exactly as the sync class bumps them.
6. `OUTBOX_DDL`, `Outbox`, `OutboxMessage` and `drain_outbox` are unchanged. Add the
   new names to `__all__` (`:186`).

## Where to change
- `src/vibey_tools/bootstrap/vibey_bootstrap/db/outbox.py` only.
- Copy the SQL of `drain_outbox` (`:159-165`) for the claim sub-select.

## Acceptance criteria
- [ ] With a recording executor, the SQL text and parameter order are asserted for every method.
- [ ] Against a real PostgreSQL (integration, skipped without `VIBEY_TEST_DATABASE_URL`), two concurrent `claim_batch` calls never return the same row.
- [ ] Against a real PostgreSQL, `reclaim_stale` returns a stale `sending` row to `pending`.
- [ ] Against a real PostgreSQL, a duplicate `enqueue` returns `False`.
- [ ] The existing sync tests pass untouched.

## Tests to write first (TDD)
- `test/db/test_outbox_async.py`:
  - `test_schema_tracked_adds_claimed_at_and_check`
  - `test_schema_untracked_matches_outbox_ddl`
  - `test_enqueue_reports_insert_versus_conflict`
  - `test_claim_batch_sql_uses_skip_locked_and_stamps_claimed_at`
  - `test_reclaim_requires_tracking`
  - `test_drainer_marks_sent_and_failed_and_never_raises`
  - `test_concurrent_claims_are_disjoint` (integration)
  - `test_reclaim_returns_stale_rows` (integration)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    (cd src/vibey_tools/bootstrap && uv run python -m pytest -q -p no:cacheprovider test/db -m "not integration")
    (cd src/vibey_tools/bootstrap && VIBEY_TEST_DATABASE_URL=${VIBEY_TEST_DATABASE_URL:-postgresql://localhost:5432/vibey_test} uv run python -m pytest -q -p no:cacheprovider test/db/test_outbox_async.py -m integration)
    (cd src/vibey_tools/bootstrap && uv run python -m mypy vibey_bootstrap/ && uv run python -m bandit -r vibey_bootstrap/ -ll -q)

## Out of scope
- vibey's `job_outbox` table (R08) and its writer (R10).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R06 — job-dispatch-envelope

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/job_dispatch.py` (new)
  - `src/vibey/domain/interfaces/job_dispatch_interface.py` (new)
  - `src/vibey/domain/errors.py` (add one exception)
  - `tests/domain/test_job_dispatch.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_errors.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
feat(domain): the job-dispatch envelope, queue names and wait-tier plan

## Why
ADR-0044 §2, §3 and §7 put four pure pieces in the domain:

- the RabbitMQ message that points at a `job` row;
- the names of every exchange and queue;
- the rule that picks a delay tier;
- the configurable prefix (12.c), so that vibey's objects stay apart from Plane's
  Celery queues on a shared broker (`deploy/helm/vibey/values.yaml:246`).

They are pure, so the domain owns them and the 100% domain floor covers them
(ADR-0023).

## Required behaviour
1. `JOB_DISPATCH_SCHEMA = "vibey.job.dispatch/1"`.
2. `@dataclass(frozen=True, slots=True) class JobDispatch`:
   - `job_id: UUID`
   - `project_id: UUID`
   - `dispatch_seq: int`, which must be ≥ 1
   - `kind: str`, which must be non-empty
   - `not_before: datetime`, which must be timezone-aware

   A violation raises `ValueError` in `__post_init__`. The property `message_id`
   returns `f"{job_id}:{dispatch_seq}"`.
3. `class JobDispatchCodec`:
   - `encode(d) -> dict[str, object]` has exactly these keys: `schema`, `job_id`,
     `project_id`, `dispatch_seq`, `kind`, `not_before` (ISO 8601).
   - `decode(raw: Mapping[str, object]) -> JobDispatch` raises the new
     `MalformedDispatch(VibeyError)` (in `domain/errors.py`) on a wrong or missing
     schema, a missing or extra key, a wrong type, a naive datetime, or a sequence
     below 1.
   - `to_bytes(d) -> bytes` is `json.dumps(encode(d), sort_keys=True)` encoded as
     UTF-8. `from_bytes(b) -> JobDispatch` decodes, and invalid JSON or UTF-8 raises
     `MalformedDispatch`.
4. `class QueueNames(prefix: str = "vibey")`, which returns exactly these strings.
   The duration label is `Ns` below 60 seconds, `Nm` for whole minutes below an hour,
   `Nh` for whole hours, and `Ns` for anything else.

   | method | returns |
   |---|---|
   | `jobs_exchange()` | `"<p>.jobs"` |
   | `project_queue(pid)` | `"<p>.jobs.<pid>"` |
   | `project_key(pid)` | `"job.<pid>"` |
   | `project_bindings(pid)` | `("job.<pid>", "*.job.<pid>")` |
   | `wait_exchange()` | `"<p>.jobs.wait"` |
   | `wait_queue(t)` | `"<p>.jobs.wait.w<label>"` |
   | `wait_key(t, pid)` | `"w<label>.job.<pid>"` |
   | `wait_binding(t)` | `"w<label>.#"` |
   | `dead_exchange()` | `"<p>.jobs.dlx"` |
   | `dead_queue()` | `"<p>.jobs.dead"` |
   | `runs_exchange()` | `"<p>.runs"` |
   | `run_queue(e)` | `"<p>.runs.<e>"` |
   | `probe_queue(e)` | `"<p>.runs.<e>.probe"` |
   | `probe_key(e)` | `"<e>.probe"` |
   | `run_dead_exchange()` | `"<p>.runs.dlx"` |
   | `run_dead_queue(e)` | `"<p>.runs.<e>.dead"` |
   | `control_exchange()` | `"<p>.runs.control"` |

5. `class WaitTierPlan(tiers_seconds: tuple[int, ...])` validates the tiers
   (non-empty, each ≥ 1, strictly ascending) and raises `ValueError` otherwise.
   `choose(remaining: timedelta) -> int | None` returns:
   - `None` when `remaining <= 0`;
   - otherwise the largest tier ≤ `remaining` (in seconds);
   - or the smallest tier when `remaining` is shorter than every tier.
6. Nothing in the module reads a clock, performs I/O or uses async.

## Where to change
- `src/vibey/domain/job_dispatch.py`.
- Copy the frozen-dataclass and validation style of `src/vibey/domain/job.py`.
- Add `MalformedDispatch` beside the other `VibeyError` subclasses in `domain/errors.py`.
- The interface module declares `JobDispatchCodecInterface`, `QueueNamesInterface` and
  `WaitTierPlanInterface`. Copy `domain/interfaces/stored_value_interface.py`.

## Acceptance criteria
- [ ] The Hypothesis round trip `decode(encode(d)) == d` holds, and so does `from_bytes(to_bytes(d)) == d`.
- [ ] Every malformed input named in behaviour 3 raises `MalformedDispatch`.
- [ ] `choose` never returns a tier longer than `remaining`, except when `remaining` is shorter than the smallest tier.
- [ ] `choose` returns `None` exactly when `remaining <= 0`.
- [ ] `test_domain_purity.py` passes; 100% domain coverage.

## Tests to write first (TDD)
- `tests/domain/test_job_dispatch.py`:
  - `test_round_trip_property` (Hypothesis)
  - `test_decode_rejects_each_malformation` (parametrized)
  - `test_message_id_is_job_and_generation`
  - `test_queue_names_table` (parametrized over the table above, with the default prefix and with `"acme"`)
  - `test_tier_labels`
  - `test_wait_plan_validation`
  - `test_choose_property` (Hypothesis)
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any broker or database code.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R07 — dispatch-miss-policy

**Lane card.**

- **Depends on:** R06.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/domain/dispatch_policy.py` (new)
  - `src/vibey/domain/interfaces/dispatch_policy_interface.py` (new)
  - `tests/domain/test_dispatch_policy.py` (new)
- **Parallel-safe with:** R04, R10, R21 and R29.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_job.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
feat(domain): decide what a dispatch that could not be claimed means

## Why
ADR-0044 §5. In the RabbitMQ backend a worker takes a delivery, then claims its row
with a fenced compare-and-set. When that claim misses, the worker must choose one of
two actions:

- drop the message, because it is stale, terminal, parked, or blocked behind a
  dependency that a release will re-dispatch;
- re-delay it, because a live lease holds it or it is not due yet.

Getting that wrong either loses a job or spins it forever, so the decision is a pure,
property-tested function. `now` is an argument, never a clock (domain purity).

## Required behaviour
1. `@dataclass(frozen=True, slots=True) class DispatchSnapshot`:
   - `state: str`, the stored `job.state` text
   - `dispatch_seq: int`
   - `run_after: datetime`
   - `lease_expires_at: datetime | None`
   - `deps_met: bool`
2. `class DispatchVerdict(StrEnum)` has two members, `DROP = "drop"` and
   `REDELAY = "redelay"`. `@dataclass(frozen=True, slots=True) class DispatchDecision`
   has `verdict`, `not_before: datetime | None` and `reason: str`.
3. `class DispatchMissPolicy.decide(snapshot: DispatchSnapshot | None, message_seq: int, now: datetime) -> DispatchDecision`.
   Apply the first rule that matches, in this order:

   | # | condition | verdict | `not_before` | reason |
   |---|---|---|---|---|
   | a | snapshot is `None` | `DROP` | — | `"unknown job"` |
   | b | `snapshot.dispatch_seq != message_seq` | `DROP` | — | `"stale generation"` |
   | c | state is `succeeded`, `failed`, `cancelled`, `awaiting_human`, `awaiting_capacity`, or anything that is not `ready` or `leased` | `DROP` | — | `"not claimable: <state>"` |
   | d | state `leased`, and `lease_expires_at` is not `None` and `>= now` | `REDELAY` | `max(lease_expires_at, run_after)` | `"held by a live lease"` |
   | e | state `ready` and `not deps_met` | `DROP` | — | `"blocked; its release will dispatch it"` |
   | f | `run_after > now` | `REDELAY` | `run_after` | `"not due"` |
   | g | anything else (a race the claim lost) | `REDELAY` | `now` | `"claim raced; retry now"` |

4. A `REDELAY` decision always has `not_before >= now`. A `DROP` decision always has
   `not_before is None`.

## Where to change
- `src/vibey/domain/dispatch_policy.py` and its interface.
- The interface declares `DispatchMissPolicyInterface.decide`. Follow the style of
  `domain/interfaces/circuit_interface.py`.

## Acceptance criteria
- [ ] Each rule a–g has a test.
- [ ] Hypothesis: for any snapshot, message sequence and `now`, a `DROP` happens whenever the sequences differ, and every `REDELAY` has `not_before >= now`.
- [ ] 100% domain coverage; the purity test passes.

## Tests to write first (TDD)
- `tests/domain/test_dispatch_policy.py`:
  - `test_rule_a_unknown_job_drops` through `test_rule_g_race_redelays_now`
  - `test_properties_hold_for_any_snapshot` (Hypothesis)
  - `test_policy_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Reading the snapshot from the database (R11).
- Acting on the decision (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R08 — dispatch-migration

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `migrations/0014_job_dispatch.sql` (new)
  - `src/vibey/infrastructure/db/orm_models.py`
  - `tests/infrastructure/db/test_orm.py` (the `EXPECTED_TABLE_NAMES` constant only)
  - `tests/infrastructure/db/test_migrator.py` (one new test)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_migrator.py`
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - `tests/infrastructure/db/test_forward_compatibility_columns.py`
  - the PostgreSQL 14–18 compatibility set in `ci.yml:188-193`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
feat(db): migration 0014 adds dispatch generations and the job outbox

## Why
ADR-0044 §4. The RabbitMQ backend needs a **dispatch generation** on every job.
`dispatch_seq = 0` means the job was never dispatched, and every new dispatch episode
increments it. It also needs a transactional outbox table in the family's outbox shape
(`vibey_bootstrap/db/outbox.py:31-42`), plus `claimed_at` so that a dead relay's
claims can be reclaimed.

The PostgreSQL backend ignores both, so this migration changes no behaviour.
Migrations are forward-only and are applied by `build_app()` under the migration lock
(`docs/plans/data-model.md` §7). `test_orm.py` requires every migrated relation to
have an ORM model (`tests/infrastructure/db/test_orm.py:50-53`, `:86-104`).

## Required behaviour
1. `migrations/0014_job_dispatch.sql` must be valid on PostgreSQL 14:
   ```sql
   -- Dispatch generations and the dispatch outbox (ADR-0044 §4).
   ALTER TABLE job ADD COLUMN dispatch_seq bigint NOT NULL DEFAULT 0;
   ALTER TABLE job ADD COLUMN dispatched_at timestamptz;
   CREATE INDEX job_ready_dispatch ON job (dispatched_at) WHERE state = 'ready';
   CREATE TABLE job_outbox (
       id               uuid PRIMARY KEY,
       idempotency_key  text UNIQUE NOT NULL,
       payload          jsonb NOT NULL,
       status           text NOT NULL DEFAULT 'pending',
       attempt_count    integer NOT NULL DEFAULT 0,
       last_error       text,
       created_at       timestamptz NOT NULL DEFAULT now(),
       sent_at          timestamptz,
       claimed_at       timestamptz,
       CONSTRAINT job_outbox_status CHECK (status IN ('pending','sending','sent','failed'))
   );
   CREATE INDEX job_outbox_pending ON job_outbox (created_at) WHERE status = 'pending';
   ```
2. `JobOrm` (`orm_models.py:237`) gains two fields:
   - `dispatch_seq: int` (BigInteger, `server_default=text("0")`, not null)
   - `dispatched_at: datetime | None` (timezone-aware)

   It also declares the `job_ready_dispatch` index. A new `JobOutboxOrm(VibeyOrmModel, table=True)`
   mirrors the table, and it is added to `ORM_TABLE_MODELS` (`:678`).
3. `EXPECTED_TABLE_NAMES` in `tests/infrastructure/db/test_orm.py:18` gains
   `"job_outbox"`. This is the only edit to an existing test file in this lane.
4. `JobRecord` and `PostgresJobRepository` are unchanged. `SELECT *` returning extra
   columns is harmless, because `_row_to_job_record` reads columns by name
   (`job_repository.py:20-42`).

## Where to change
- `migrations/0014_job_dispatch.sql`
- `src/vibey/infrastructure/db/orm_models.py`: copy `HumanGateOrm` (`:553`) for the
  new model, and the `JobOrm` column style for the new columns.
- `tests/infrastructure/db/test_orm.py:18`
- `tests/infrastructure/db/test_migrator.py`: add the new test

## Acceptance criteria
- [ ] A fresh database migrates. A second apply is a no-op. The checksum guard is unchanged.
- [ ] `test_orm_columns_match_every_migrated_relation` passes with the new columns and table.
- [ ] The chaos test and `test_job_repository.py` pass unchanged.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_migrator.py`:
  `test_job_dispatch_migration_adds_generation_and_outbox`. It asserts that
  `job.dispatch_seq` defaults to 0 on an inserted row, that `job_outbox` exists, and
  that the `status` CHECK refuses `'bogus'`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Writing or reading `dispatch_seq` and `job_outbox` (R10, R11).
- `docs/plans/data-model.md` (R35).
- CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R09 — reap-bound

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/infrastructure/db/job_repository.py` (`reap` only)
  - `tests/infrastructure/db/test_job_repository.py` (new tests only)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected; `max_attempts=1000` keeps it
    clear of the new bound)
  - `tests/infrastructure/db/test_human_gate_repository.py`
  - `tests/application/test_worker.py`
  - all protected tests
- **Standing constraints:** see the list above.

## Title
fix(queue): reaping bounds a job that keeps killing its worker

## Why
ADR-0044 §8, and ADR-0024: every bounded ladder parks with a grant. Neither the claim
nor the reaper bounds a job that takes its worker down:

- the claim increments `attempts` with no upper bound
  (`src/vibey/infrastructure/db/job_repository.py:182-187`);
- `reap()` re-readies every expired lease unconditionally (`:311-320`).

A handler that kills its process on every attempt therefore never reaches
`_settle_failure` (`src/vibey/application/worker.py:224-272`), and it is re-claimed
forever. The RabbitMQ backend bounds the same failure through the broker's delivery
limit. This lane gives the PostgreSQL backend the same bound under the same gate kind,
`delivery_exhausted`.

## Required behaviour
1. `PostgresJobRepository.reap()` runs one transaction with two statements.
   - **(a)** Every row with `state = 'leased' AND lease_expires_at < now() AND attempts >= max_attempts`
     becomes `awaiting_human`: `lease_owner` and `lease_expires_at` are set to NULL,
     `attempts = greatest(attempts - 1, 0)` (one attempt refunded), and
     `updated_at = now()`. One `human_gate` row is inserted per parked job:
     - `kind = 'delivery_exhausted'`
     - its `project_id` and `job_id`
     - `prompt = format('job %L was abandoned mid-run on each of its %s deliveries (its worker died, was killed, or lost its lease every time). Answer anything to retry it once.', kind, max_attempts)`

     Use one statement with a data-modifying CTE (`WITH exhausted AS (UPDATE … RETURNING …) INSERT INTO human_gate … SELECT … FROM exhausted RETURNING gate_id`).
     Then send `NOTIFY vibey_gate_raised, '<gate_id>'` per gate, in the same
     transaction, as `raise_gate` does (`human_gate_repository.py:58`).
   - **(b)** Today's re-ready SQL (`:314-318`), restricted to `attempts < max_attempts`.
2. It returns the count from (a) plus the count from (b).
3. A gate raised by (a) is answered through the ordinary path
   (`human_gate_repository.py:61-86`), which re-readies the job. Each answer therefore
   buys exactly one more delivery.
4. Nothing else in the class changes.
5. **Stop rule:** if an existing test in `test_job_repository.py` asserts that `reap()`
   re-readies a row whose `attempts >= max_attempts`, stop and report. Do not edit
   that test.

## Where to change
- `src/vibey/infrastructure/db/job_repository.py:311-320`. Keep `_rowcount` (`:370`).

## Acceptance criteria
- [ ] A job with `max_attempts=1`, claimed once with an expired lease, is `awaiting_human` after `reap()`, with `attempts = 0` and one open `delivery_exhausted` gate; `reap()` returns 1.
- [ ] A job with attempts left is re-readied as before.
- [ ] Answering the gate re-readies the job, and it can be claimed again.
- [ ] Every existing repository test and the chaos test pass unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_job_repository.py` (new tests only):
  - `test_reap_parks_a_job_whose_every_delivery_was_abandoned`
  - `test_reap_counts_parked_and_rereadied_together`
  - `test_answering_a_delivery_exhausted_gate_rereadies_the_job`
  - `test_reap_park_notifies_the_raised_gate` (LISTEN on a second connection and assert the gate id arrives)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/application/test_worker.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The RabbitMQ backend's reap (R11).
- The worker loop.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R10 — dispatch-records-enqueue

**Lane card.**

- **Depends on:** R05, R06, R08.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/db/dispatch_records.py` (new)
  - `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py` (new)
  - `tests/infrastructure/db/test_dispatch_records.py` (new)
- **Parallel-safe with:** R04, R07, R21 and R29. R11 follows it on the same file.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - `tests/infrastructure/db/test_build_decompose_fan_out.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(db): enqueue and dependency release record their dispatches

## Why
ADR-0044 §4. When a job becomes claimable it must get a dispatch generation and an
outbox row **in the same transaction** as the state change. There are two such moments:

- it is enqueued with every dependency already met;
- the ack of its last dependency commits.

Otherwise a crash between the commit and the publish could lose the dispatch.
`PostgresJobRepository` already owns the enqueue SQL
(`src/vibey/infrastructure/db/job_repository.py:66-134`) and the fenced ack
(`:223-235`). The RabbitMQ backend reuses both through a subclass and adds only the
dispatch-writing steps. The PostgreSQL backend class is not modified.

## Required behaviour
1. `class DispatchOutboxWriter` has one method,
   `async def write(conn: asyncpg.Connection, dispatch: JobDispatch, *, key_suffix: str = "") -> bool`.
   It builds
   `vibey_bootstrap.db.outbox.AsyncOutbox(conn, table="job_outbox", track_claims=True)`
   (from R05) and enqueues the idempotency key `f"dispatch:{dispatch.job_id}:{dispatch.dispatch_seq}{key_suffix}"`
   with payload `JobDispatchCodec().encode(dispatch)` (from R06). It returns whether a
   row was inserted.
2. `class DispatchingJobRecords(PostgresJobRepository)` takes `pool` and
   `writer: DispatchOutboxWriterInterface`.
3. It overrides `_enqueue_on(conn, request, enqueued)`. It calls `super()._enqueue_on(...)`
   first, then runs this statement in the same transaction:
   ```sql
   UPDATE job SET dispatch_seq = 1, dispatched_at = NULL
   WHERE id = $1 AND state = 'ready' AND dispatch_seq = 0
     AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                     WHERE d.job_id = job.id AND p.state <> 'succeeded')
   RETURNING id, project_id, dispatch_seq, kind, run_after
   ```
   A returned row gets one outbox row with `not_before = run_after`. A replayed
   enqueue, where the row exists and `dispatch_seq` is already ≥ 1, writes nothing.
4. `async def ack_and_release(self, job_id, *, owner) -> tuple[bool, tuple[JobDispatch, ...]]`
   runs one transaction:
   - Run today's ACK SQL (`job_repository.py:227-231`). If its rowcount is not 1,
     return `(False, ())` and change nothing else.
   - Otherwise run:
     ```sql
     UPDATE job j SET dispatch_seq = 1, dispatched_at = NULL
     WHERE j.state = 'ready' AND j.dispatch_seq = 0
       AND EXISTS (SELECT 1 FROM job_dependency d WHERE d.job_id = j.id AND d.depends_on_job_id = $1)
       AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                       WHERE d.job_id = j.id AND p.state <> 'succeeded')
     RETURNING j.id, j.project_id, j.dispatch_seq, j.kind, j.run_after
     ```
   - Write one outbox row per released job, and return `(True, dispatches)`.
5. `ack()` is overridden to `return (await self.ack_and_release(job_id, owner=owner))[0]`,
   so the class still satisfies the `JobRepository` Protocol
   (`application/interfaces/queue.py:89`).
6. The class never publishes. Publishing belongs to the relay (R13).

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py`.
- The interface module declares `DispatchOutboxWriterInterface` and
  `DispatchingJobRecordsInterface`. Copy
  `infrastructure/db/interfaces/job_repository_interface.py` for the TYPE_CHECKING-only
  imports.
- `vibey.infrastructure.db.interfaces` is already in `.importlinter`'s
  `infrastructure-interfaces-declare-only` contract.

## Acceptance criteria
- [ ] Enqueueing a job with no dependencies gives `dispatch_seq = 1` and exactly one `pending` `job_outbox` row, whose payload decodes to the `JobDispatch`.
- [ ] Enqueueing again with the same key leaves one outbox row and `dispatch_seq = 1`.
- [ ] A job with an unmet dependency stays at `dispatch_seq = 0` with no outbox row.
- [ ] In a batch where B depends on A: A is at 1 and B at 0. A batch rolled back by a bad dependency key leaves no outbox rows.
- [ ] Acking A releases B (B goes to 1 with an outbox row). An ack by a non-owner releases nothing and returns `(False, ())`.
- [ ] A dependent with two dependencies is released only by the second ack.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/db/test_dispatch_records.py` (uses the `migrated_pool` and
  `project_id` fixtures from `tests/infrastructure/db/conftest.py:62-71`):
  - `test_claimable_enqueue_writes_one_dispatch`
  - `test_replayed_enqueue_writes_nothing_more`
  - `test_blocked_enqueue_writes_no_dispatch`
  - `test_batch_dispatches_only_its_claimable_rows`
  - `test_rolled_back_batch_leaves_no_outbox_rows`
  - `test_ack_releases_the_dependents_it_unblocks`
  - `test_non_owner_ack_releases_nothing`
  - `test_second_of_two_dependencies_releases`
  - `test_records_satisfy_the_job_repository_protocol`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The claim, nack, defer, reap and sweep transitions (R11).
- Publishing (R13).
- The PostgreSQL backend class.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R11 — dispatch-records-settle

**Lane card.**

- **Depends on:** R07, R09, R10.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/db/dispatch_records.py`
  - `src/vibey/infrastructure/db/interfaces/dispatch_records_interface.py`
  - `tests/infrastructure/db/test_dispatch_records.py`
- **Parallel-safe with:** R12, R15, R22 and R24.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_job_repository.py`
  - `tests/infrastructure/db/test_chaos.py` (protected)
  - R10's tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(db): the fenced dispatch claim, redispatching settles, the lost-dispatch sweep and the dead-letter park

## Why
ADR-0044 §4, §5 and §8. Six things are needed:

- a fenced claim by job id **and** generation, which also takes over an expired lease
  (this replaces the `SKIP LOCKED` scan for the RabbitMQ backend);
- every settle that starts a new dispatch episode (nack with attempts left, defer, and
  reap) increments the generation and writes an outbox row in its own transaction;
- a sweep that re-dispatches claimable jobs whose message looks lost, which also
  closes the enqueue-versus-ack race R10 leaves open;
- a dead-letter park that turns a poison pointer into a `delivery_exhausted` gate
  (ADR-0024);
- the fences stay exactly the PostgreSQL backend's (`job_repository.py:223-309`);
- the bounded reap is R09's.

## Required behaviour
1. `claim_dispatched(dispatch: JobDispatch, *, owner: str, lease: timedelta) -> JobRecord | None`:
   ```sql
   UPDATE job SET state='leased', lease_owner=$4, lease_expires_at=now()+$5::interval,
                  attempts=attempts+1, updated_at=now()
   WHERE id=$1 AND project_id=$3 AND dispatch_seq=$2
     AND (state='ready' OR (state='leased' AND lease_expires_at < now()))
     AND run_after <= now()
     AND NOT EXISTS (SELECT 1 FROM job_dependency d JOIN job p ON p.id = d.depends_on_job_id
                     WHERE d.job_id = job.id AND p.state <> 'succeeded')
   RETURNING *
   ```
   Map the row with the same row mapper `PostgresJobRepository` uses.
2. `snapshot(job_id) -> DispatchSnapshot | None` (from R07) selects `state`,
   `dispatch_seq`, `run_after`, `lease_expires_at`, and `deps_met` computed with the
   same `NOT EXISTS`.
3. `nack` is overridden. Use today's NACK SQL (`job_repository.py:241-251`) with two
   changes:
   - `dispatch_seq = CASE WHEN attempts >= max_attempts THEN dispatch_seq ELSE dispatch_seq + 1 END`
   - `dispatched_at = NULL`

   Add `RETURNING id, project_id, state, dispatch_seq, kind, run_after`. When the
   returned state is `ready`, write an outbox row with `not_before = run_after`, in the
   same transaction. Return whether a row was updated.
4. `defer` is overridden the same way from today's DEFER SQL (`:298-303`): always
   `dispatch_seq + 1` and an outbox row with `not_before = retry_at`.
5. `reap` is overridden. Keep R09's parking statement (a) unchanged. Its re-ready
   statement (b) also sets `dispatch_seq = dispatch_seq + 1` and `dispatched_at = NULL`,
   and returns the rows, each of which gets an outbox row. Return the count from (a)
   plus (b).
6. `sweep_lost(*, redispatch_after: timedelta, limit: int = 500) -> int` runs one
   transaction:
   - Select candidate rows:
     ```sql
     SELECT id, project_id, dispatch_seq, kind, run_after FROM job j
     WHERE j.state='ready' AND j.run_after <= now()
       AND (j.dispatch_seq = 0 OR j.dispatched_at < now() - $1::interval)
       AND NOT EXISTS (<deps unmet>)
     ORDER BY j.run_after ASC LIMIT $2 FOR UPDATE SKIP LOCKED
     ```
   - A row at seq 0 is updated to seq 1 and written with the plain key.
   - A row at seq ≥ 1 is written again with the **same** generation and
     `key_suffix=f":sweep:{int(epoch)}"`, where `epoch` is the database's
     `extract(epoch from now())`. This is a harmless duplicate that keeps the job's
     FIFO position.
   - Every swept row gets `dispatched_at = now()`, so the next sweep waits.
   - Return the number of rows written.
7. `mark_dispatched(job_id, dispatch_seq) -> bool` runs
   `UPDATE job SET dispatched_at = now() WHERE id=$1 AND dispatch_seq=$2`.
8. `park_dead_letter(dispatch: JobDispatch, *, delivery_limit: int) -> bool` runs one
   transaction:
   - It first tries:
     ```sql
     UPDATE job SET state='awaiting_human', lease_owner=NULL, lease_expires_at=NULL,
            attempts=greatest(attempts-1,0), updated_at=now()
     WHERE id=$1 AND dispatch_seq=$2
       AND (state='ready' OR (state='leased' AND lease_expires_at < now()))
     RETURNING project_id, kind
     ```
   - If no row comes back, return `False`.
   - Otherwise insert a `human_gate` with `kind='delivery_exhausted'` and the prompt
     `f"job {kind!r} was delivered {delivery_limit} times and every consumer holding it died. Answer anything to retry it with a fresh delivery budget."`,
     send `NOTIFY vibey_gate_raised`, and return `True`.
9. The exactly-once commit fence is unchanged: `ack`, `park`, `heartbeat`,
   `grant_attempts` and `assign_engine` are inherited as they are.

## Where to change
- `src/vibey/infrastructure/db/dispatch_records.py` (append to R10's class).
- Extend its interface.
- Reuse R09's parking CTE text; do not duplicate it. Move it to a class constant on
  `PostgresJobRepository`, for example `_REAP_PARK_SQL`, and reference it from both
  classes.

## Acceptance criteria
- [ ] The claim hits for a ready row at a matching generation, takes over an expired lease, and misses on a stale generation, a future `run_after`, an unexpired lease or an unmet dependency.
- [ ] `snapshot` feeds `DispatchMissPolicy` correctly in each miss case.
- [ ] A nack with attempts left bumps the generation and writes an outbox row at `run_after`. A nack at the last attempt fails the job with no outbox row.
- [ ] A defer bumps the generation and writes an outbox row at `retry_at`.
- [ ] A reap re-readies with a bump and an outbox row, and still parks exhausted rows (R09).
- [ ] The sweep dispatches the seq-0 race and old dispatches, skips rows with a pending outbox (`dispatched_at IS NULL` and seq ≥ 1), and throttles itself.
- [ ] `mark_dispatched` ignores a stale generation.
- [ ] `park_dead_letter` parks and raises a gate only when the row is still claimable at that generation.
- [ ] An ack from a stale owner after a reap-redispatch is refused.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
Add to `tests/infrastructure/db/test_dispatch_records.py`:
- `test_claim_dispatched_hits_and_leases`
- `test_claim_dispatched_takes_over_an_expired_lease`
- `test_claim_dispatched_misses_each_way` (parametrized over the five miss causes)
- `test_snapshot_reports_deps_and_lease`
- `test_nack_with_attempts_left_redispatches_at_run_after`
- `test_nack_at_the_last_attempt_fails_without_dispatch`
- `test_defer_redispatches_at_retry_at`
- `test_reap_redispatches_and_still_parks_exhausted`
- `test_sweep_dispatches_the_seq_zero_race`
- `test_sweep_duplicates_an_old_dispatch_at_the_same_generation`
- `test_sweep_skips_a_pending_outbox_row`
- `test_sweep_throttles_itself`
- `test_mark_dispatched_ignores_a_stale_generation`
- `test_park_dead_letter_parks_only_a_claimable_row`
- `test_stale_owner_ack_after_reap_is_refused`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Publishing (R13).
- Consuming (R14).
- The repository that composes these pieces (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R12 — queue-topology

**Lane card.**

- **Depends on:** R04, R06.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/queue/__init__.py` (new)
  - `src/vibey/infrastructure/queue/rabbitmq_topology.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/{__init__,rabbitmq_topology_interface}.py` (new)
  - `.importlinter`
  - `tests/infrastructure/queue/{__init__,conftest,test_rabbitmq_topology,test_rabbitmq_topology_integration}.py` (new)
- **Parallel-safe with:** R11, R15, R22 and R24. It is last in the `.importlinter` chain, after R21.
- **Must keep passing unchanged:**
  - `tests/meta/test_import_contracts_bind.py`
  - `tests/infrastructure/test_sovereign_surfaces.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(queue): declare the RabbitMQ topology for jobs

## Why
ADR-0044 §2 names every exchange and queue the job backend uses. It also fixes their
arguments:

- quorum work queues with a delivery limit, at-least-once dead-lettering and a
  per-queue consumer timeout;
- TTL wait tiers that dead-letter back into the dispatch exchange;
- one dead queue.

Declaring them in code at start is sub-doctrine 12.c: the topology is declared, not
clicked. This lane also carries the first integration checks of the upstream facts the
ADR says it owes (the pinned `rabbitmq:4-management-alpine`, `values.yaml:434-440`).

## Required behaviour
1. `class RabbitMqJobTopology(client: AmqpClientInterface, names: QueueNamesInterface, settings: QueueRabbitMqConfigInterface)`.
2. `async def declare_base(self) -> None` declares:
   - exchanges `names.jobs_exchange()` (topic), `names.wait_exchange()` (topic) and
     `names.dead_exchange()` (fanout);
   - the queue `names.dead_queue()` with `{"x-queue-type": "quorum"}`, bound to the
     dead exchange with key `""`;
   - for every tier in `settings.wait_tiers_seconds`, the queue
     `names.wait_queue(t)` with `{"x-queue-type": "classic", "x-message-ttl": t*1000, "x-dead-letter-exchange": names.jobs_exchange()}`,
     bound with `names.wait_binding(t)`.

   It is idempotent, and it runs its declarations once per instance.
3. `def project_arguments(self) -> dict[str, object]` returns exactly:
   ```python
   {"x-queue-type": "quorum", "x-delivery-limit": delivery_limit,
    "x-dead-letter-exchange": names.dead_exchange(),
    "x-dead-letter-strategy": "at-least-once", "x-overflow": "reject-publish",
    "x-consumer-timeout": consumer_timeout_seconds * 1000}
   ```
4. `async def declare_project(self, project_id: UUID) -> str` calls `declare_base()`
   if needed. It then declares `names.project_queue(pid)` with `project_arguments()`,
   binds both of `names.project_bindings(pid)` to the jobs exchange, and caches the
   project id. It returns the queue name.
5. `.importlinter`: `vibey.infrastructure.queue.interfaces` joins the
   `source_modules` of `[importlinter:contract:infrastructure-interfaces-declare-only]`
   (`.importlinter:98-120`).
6. `tests/infrastructure/queue/conftest.py` re-exports the database fixtures, so that
   later lanes can use Postgres here:
   `from tests.infrastructure.db.conftest import database_url, pg_pool, migrated_pool, project_id  # noqa: F401`.
   It also provides `amqp_url` (skip unless `VIBEY_TEST_AMQP_URL` is set) and
   `memory_amqp` (a fresh `InMemoryAmqpClient`).

## Where to change
- The new package. Copy the layout of `src/vibey/infrastructure/bus/`
  (`rabbitmq.py` + `interfaces/rabbitmq_interface.py`).
- `.importlinter:98-120`.

## Acceptance criteria
- [ ] Against the in-memory client, every exchange, queue, argument and binding in behaviours 2–4 is declared exactly once, however often it is called.
- [ ] A message published to `job.<pid>` lands in the project queue. A message published to `names.wait_key(1, pid)` lands in `vibey.jobs.wait.w1s`, and after `expire()` it lands in the project queue.
- [ ] Integration, with a real broker: the declarations succeed, including `x-consumer-timeout` and `x-delivery-limit` on a quorum queue; a declaration made twice succeeds; a message sent to the 1 s wait tier reaches the project queue within 3 s.
- [ ] `lint-imports` passes, and so does `test_import_contracts_bind.py`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_rabbitmq_topology.py`:
  - `test_declare_base_declares_exchanges_dead_queue_and_tiers`
  - `test_project_arguments_are_exact`
  - `test_declare_project_binds_both_keys_and_is_idempotent`
  - `test_wait_tier_expiry_routes_back_to_the_project_queue`
  - `test_topology_satisfies_its_interface`
- `tests/infrastructure/queue/test_rabbitmq_topology_integration.py` (integration):
  - `test_real_broker_accepts_every_argument`
  - `test_real_wait_tier_returns_the_message`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Loop-service topology (R22 and R23).
- Publishing and consuming (R13, R14).
- The chart.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R13 — dispatch-relay

**Lane card.**

- **Depends on:** R05, R08, R10, R12.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/queue/dispatch_relay.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/dispatch_relay_interface.py` (new)
  - `tests/infrastructure/queue/test_dispatch_relay.py` (new)
- **Parallel-safe with:** R14, R23, R25 and R26.
- **Must keep passing unchanged:**
  - R10, R11 and R12 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(queue): the outbox relay publishes each dispatch to the right exchange

## Why
ADR-0044 §4 and §7. The outbox rows R10 and R11 write must reach the broker with
publisher confirms. The relay is what gives at-least-once publish:

- a due dispatch goes straight to the dispatch exchange;
- a future dispatch goes to the largest wait tier no longer than its remaining delay;
- a row is marked sent, and the job's `dispatched_at` stamped, only after the confirm;
- rows a crashed relay left in `sending` are reclaimed through R05's `reclaim_stale`.

## Required behaviour
1. `class DispatchRelay` is constructed with:
   - `pool: asyncpg.Pool`
   - `client: AmqpClientInterface`
   - `names: QueueNamesInterface`
   - `topology: RabbitMqJobTopologyInterface`
   - `tiers: WaitTierPlanInterface`
   - `records: DispatchingJobRecordsInterface`
   - `clock: Clock` (`application/interfaces`)
   - `logger: Logger`
2. `async def publish(self, dispatch: JobDispatch) -> None`:
   - Compute `remaining = dispatch.not_before - clock.now()` and
     `tier = tiers.choose(remaining)`.
   - Call `await topology.declare_project(dispatch.project_id)`.
   - When `tier is None`, publish to `names.jobs_exchange()` with key
     `names.project_key(pid)`. Otherwise publish to `names.wait_exchange()` with key
     `names.wait_key(tier, pid)`.
   - The body is `JobDispatchCodec().to_bytes(dispatch)`. The properties are
     `message_id=dispatch.message_id`, `type="job.dispatch"`,
     `correlation_id=DELIVERY_CORRELATION.for_project(pid).value` (from
     `domain/correlation.py`) and `delivery_mode=2`.
   - It raises `AmqpPublishError` on a failed confirm.
3. `async def drain(self, limit: int = 100) -> int`:
   - Acquire a connection.
   - Call `AsyncOutbox(conn, table="job_outbox", track_claims=True).reclaim_stale(60)`.
   - Build an `AsyncOutboxDrainer` whose sender decodes the payload with the codec,
     calls `publish`, then calls `records.mark_dispatched(job_id, seq)`.
   - Return the count sent.
4. `async def flush_soon(self) -> None` calls `drain(20)`. It logs any exception at
   `warning` as `queue.relay_failed` and never raises. It is the best-effort fast path
   that runs after a commit.
5. A publish that fails leaves the row back at `pending` with `attempt_count+1`, via
   R05's `mark_failed`, and `dispatched_at` untouched.

## Where to change
- The new module, beside `rabbitmq_topology.py`, with its interface.

## Acceptance criteria
- [ ] With a real Postgres and the in-memory broker, a claimable enqueue followed by `drain()` puts one message in the project queue. The body decodes to the job's dispatch, and `dispatched_at` is set.
- [ ] A dispatch 90 s in the future goes to the `w30s` tier. After `expire()` it lands in the project queue with the routing key kept.
- [ ] A publish refusal returns the outbox row to `pending` and leaves `dispatched_at` NULL.
- [ ] A stale `sending` row is reclaimed and published.
- [ ] `flush_soon` never raises.
- [ ] Integration, with a real broker: the tier round trip keeps the routing key.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_dispatch_relay.py`:
  - `test_due_dispatch_goes_to_the_project_queue`
  - `test_future_dispatch_goes_to_the_largest_fitting_tier`
  - `test_expired_tier_message_reaches_the_project_queue`
  - `test_failed_publish_leaves_the_row_pending`
  - `test_stale_sending_row_is_reclaimed_and_sent`
  - `test_flush_soon_swallows_and_logs`
  - `test_real_broker_tier_round_trip` (integration)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/infrastructure/db/test_dispatch_records.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Consuming (R14).
- The repository (R16).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R14 — project-deliveries

**Lane card.**

- **Depends on:** R12.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/queue/{project_deliveries,rabbitmq_wakeup}.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/{project_deliveries_interface,rabbitmq_wakeup_interface}.py` (new)
  - `tests/infrastructure/queue/{test_project_deliveries,test_rabbitmq_wakeup}.py` (new)
- **Parallel-safe with:** R13, R23, R25 and R26.
- **Must keep passing unchanged:**
  - R12 tests
  - `tests/infrastructure/db/test_notifier.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(queue): buffer a project's deliveries, hold them as leases, and wake the worker

## Why
ADR-0044 §5 and §11. In the RabbitMQ backend the broker's lease is a *held delivery*:
a message pushed under `basic.qos prefetch = worker parallelism`, kept unacknowledged
while its job runs. Four things follow:

- a worker's `claim()` takes the next *buffered* delivery;
- the same push is the wakeup that replaces `LISTEN vibey_job_ready`
  (`src/vibey/infrastructure/db/notifier.py:16-51`);
- on SIGTERM, deliveries that were buffered but never claimed must go back to the
  queue at once (ADR-0025, ADR-0026);
- held deliveries settle as their jobs finish.

## Required behaviour
1. `class ProjectDeliveries(client, topology, *, prefetch: int = 1)`:
   - `set_prefetch(n: int)` is allowed only before the first `ensure_started`. It
     raises `RuntimeError` afterwards, and `ValueError` for `n < 1`.
   - `async def ensure_started(project_id)` runs once per instance. It calls
     `topology.declare_project` and `client.consume(queue, prefetch=..., handler=...)`.
     The handler appends each delivery to an `asyncio.Queue` and sets an
     `asyncio.Event`. Only one project per instance is allowed; a second project id
     raises `RuntimeError`, because a worker serves one project (`cli/main.py:1549-1566`).
   - `next_buffered() -> AmqpDeliveryInterface | None` takes the next delivery without
     waiting, and clears the event when the buffer empties.
   - `async def wait_buffered(timeout: timedelta) -> bool`.
   - `hold(job_id, delivery)` records the delivery as the job's broker lease.
   - `async def settle_held(job_id) -> bool` completes (acks) the held delivery and
     forgets it. It returns `False` if nothing is held.
   - `async def stop() -> int` cancels the consumer, abandons every buffered-but-unheld
     delivery (`nack(requeue=True)`), and returns how many it returned. Held deliveries
     are left alone; their jobs are still running.
2. `class RabbitMqJobWakeup(deliveries)` implements `JobReadyNotifier`
   (`application/interfaces/queue.py:81-86`).
   `wait_for_job_ready(project_id, *, timeout)` calls `ensure_started` and returns
   `wait_buffered(timeout)`: `True` when a delivery was pushed, `False` on timeout.

## Where to change
- The two new modules and their interfaces.

## Acceptance criteria
- [ ] Using the in-memory client, no more than `prefetch` deliveries are ever unsettled.
- [ ] `hold` and `settle_held` ack exactly the held one.
- [ ] `stop()` returns buffered deliveries with their delivery count incremented, and keeps held ones.
- [ ] A second project id raises.
- [ ] `set_prefetch` after start raises.
- [ ] The wakeup returns `True` on a push and `False` on a timeout.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_project_deliveries.py`:
  - `test_prefetch_bounds_the_buffer`
  - `test_hold_then_settle_acks_that_delivery`
  - `test_stop_returns_unheld_buffered_deliveries`
  - `test_one_project_per_instance`
  - `test_prefetch_is_fixed_once_started`
- `tests/infrastructure/queue/test_rabbitmq_wakeup.py`:
  - `test_wakes_on_push`
  - `test_times_out_without_push`
  - `test_wakeup_satisfies_job_ready_notifier`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The claim logic (R16).
- CLI wiring (R17).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R15 — gate-redispatch

**Lane card.**

- **Depends on:** R10.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/db/human_gate_repository.py`
  - `tests/infrastructure/db/test_human_gate_repository.py` (new tests only)
- **Parallel-safe with:** R11, R12, R22 and R24.
- **Must keep passing unchanged:**
  - every existing test in `tests/infrastructure/db/test_human_gate_repository.py`
  - `tests/infrastructure/test_operator_handlers.py`
  - `tests/cli/test_main_integration.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(gates): answering a gate re-dispatches its job

## Why
ADR-0044 §6. A parked job holds no delivery. Its answer re-readies it in the same
transaction as the answer (`src/vibey/infrastructure/db/human_gate_repository.py:61-86`).
In the RabbitMQ backend, that same transaction must also start a new dispatch episode
and write its outbox row, or the answered job would sit `ready` with no message until
the lost-dispatch sweep found it.

The PostgreSQL backend's SQL stays exactly as it is today.

## Required behaviour
1. `PostgresHumanGateRepository.__init__(pool, *, dispatch_writer: DispatchOutboxWriterInterface | None = None)`.
   The default `None` keeps today's behaviour byte for byte.
2. With a writer set, the re-ready statement in `answer` becomes:
   ```sql
   UPDATE job SET state='ready', updated_at=now(),
                  dispatch_seq=dispatch_seq+1, dispatched_at=NULL
   WHERE id=$1 AND state='awaiting_human'
   RETURNING id, project_id, dispatch_seq, kind, run_after
   ```
   A returned row gets one outbox row (`not_before = run_after`) through the writer, in
   the same transaction. The `NOTIFY vibey_job_ready` stays.
3. Answering a gate whose job is no longer `awaiting_human` writes no outbox row. That
   is today's guard.

## Where to change
- `human_gate_repository.py:34-86`.
- Import only the writer's interface, from `infrastructure/db/interfaces/dispatch_records_interface.py`.

## Acceptance criteria
- [ ] With no writer, the SQL and the effects are unchanged, and the existing tests pass.
- [ ] With a writer, the answer bumps the generation and writes exactly one outbox row.
- [ ] An answer to a gate whose job moved on writes none.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
Add to `tests/infrastructure/db/test_human_gate_repository.py`:
- `test_answer_with_a_dispatch_writer_redispatches_the_job`
- `test_answer_writes_no_dispatch_when_the_job_moved_on`
- `test_answer_without_a_writer_is_unchanged`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Composing the writer into `build_app` (R17).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R16 — rabbitmq-job-repository

**Lane card.**

- **Depends on:** R11, R13, R14, R15.
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/queue/rabbitmq_job_repository.py` (new)
  - `src/vibey/infrastructure/queue/interfaces/rabbitmq_job_repository_interface.py` (new)
  - `tests/infrastructure/queue/test_rabbitmq_job_repository.py` (new)
- **Parallel-safe with:** nothing in `infrastructure/queue` (it imports all of it). The loop-service lanes can run beside it.
- **Must keep passing unchanged:**
  - `tests/fakes/test_port_parity.py`
  - `tests/application/test_worker.py`
  - `tests/infrastructure/db/*`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(queue): RabbitMqJobRepository, the RabbitMQ backend of the job queue

## Why
ADR-0044 §1, §5, §8 and §11. This lane composes the pieces into the `JobRepository`
Protocol (`src/vibey/application/interfaces/queue.py:89-186`):

- the fenced records (R10, R11);
- the relay (R13);
- the held deliveries (R14);
- the miss policy (R07).

`WorkerLoop` (`application/worker.py:130-312`) must run on it unchanged. That is the
point of the port.

## Required behaviour
1. `class RabbitMqJobRepository` is constructed with:
   - `records: DispatchingJobRecordsInterface`
   - `relay: DispatchRelayInterface`
   - `deliveries: ProjectDeliveriesInterface`
   - `policy: DispatchMissPolicyInterface`
   - `codec: JobDispatchCodecInterface`
   - `client: AmqpClientInterface`, used only to read the dead queue
   - `names: QueueNamesInterface`
   - `settings: QueueRabbitMqConfigInterface`
   - `clock: Clock`
   - `logger: Logger`
2. The read and write methods that involve no broker delegate straight to `records`:
   `enqueue`, `enqueue_batch`, `list_for_cycle`, `heartbeat`, `grant_attempts`,
   `assign_engine`, `count_unsettled`, `queue_depth` and `get`. `enqueue` and
   `enqueue_batch` then `await relay.flush_soon()`.
3. `claim(project_id, *, owner, lease)`:
   - Call `await deliveries.ensure_started(project_id)`. On the **first** claim of
     this instance, if nothing is buffered, `await deliveries.wait_buffered(first_claim_wait_seconds)`.
   - Then loop:
     - `d = deliveries.next_buffered()`; if it is `None`, return `None`.
     - Decode `d.body`. On `MalformedDispatch`, or a dispatch whose `project_id` is not
       `project_id`, call `d.dead_letter()`, log `queue.malformed_dispatch`, and
       continue.
     - `job = records.claim_dispatched(dispatch, owner=owner, lease=lease)`. If there
       is a job: `deliveries.hold(job.id, d)` and return it.
     - Otherwise:
       - Call `decision = policy.decide(await records.snapshot(dispatch.job_id), dispatch.dispatch_seq, clock.now())`.
       - On `REDELAY`, call `relay.publish(replace(dispatch, not_before=decision.not_before))`
         and then `d.complete()`. If the publish raises, call `d.abandon()` instead and
         return `None`, so the message is never lost.
       - On `DROP`, call `d.complete()`.
       - Log `queue.dispatch_missed` with the reason at `info`, and continue.
4. `ack`, `nack`, `defer` and `park` each call the matching `records` method, then
   **always** `await deliveries.settle_held(job_id)`, whether or not the write landed
   (a refused write means the delivery is stale), then `await relay.flush_soon()`.
   Each returns the records method's boolean.
5. `reap()` is the reconciler, and it is throttled to run at most once per
   `reconcile_interval_seconds` by `clock`. When throttled it returns 0. Otherwise it
   runs, in order:
   - `n = records.reap()`
   - `records.sweep_lost(redispatch_after=...)`
   - `relay.drain()`
   - drain up to 100 dead pointers: `d = await client.get(names.dead_queue())` until it
     returns `None`. Decode each one, call
     `records.park_dead_letter(dispatch, delivery_limit=settings.delivery_limit)`, then
     `d.complete()`. A malformed dead pointer is completed and logged at `warning` with
     its first 200 bytes.

   It returns `n`. Every step's exception is logged and does not stop the later steps.
6. `stop()` returns `await deliveries.stop()`, for the drain.

## Where to change
- The new module and its interface. Copy the settle-then-log discipline of
  `WorkerLoop._landed` (`worker.py:425-442`): log refused writes and never raise.

## Acceptance criteria
- [ ] Using a real Postgres and the in-memory broker, one `WorkerLoop` (`application/worker.py`) runs enqueue → claim → handler `Success` → ack. The job is `succeeded` and the delivery acked.
- [ ] A `Park` leaves no delivery. Answering the gate (with R15's writer) makes the job claimable again after `reap()`.
- [ ] A `Defer` re-delays the job, and it is claimable after `expire()` of its tier.
- [ ] A stale-generation delivery is dropped. A live-lease delivery is re-delayed.
- [ ] A malformed delivery is dead-lettered.
- [ ] `reap()` parks a dead-lettered pointer's job as `delivery_exhausted`.
- [ ] `reap()` is throttled.
- [ ] The instance satisfies `JobRepository` (`isinstance`).
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_rabbitmq_job_repository.py`:
  - `test_worker_loop_runs_a_job_end_to_end`
  - `test_park_holds_no_delivery_and_answer_redispatches`
  - `test_defer_redelays_through_a_tier`
  - `test_stale_generation_is_dropped`
  - `test_live_lease_is_redelayed`
  - `test_redelay_publish_failure_abandons_instead_of_losing`
  - `test_malformed_delivery_is_dead_lettered`
  - `test_reap_parks_dead_lettered_jobs`
  - `test_reap_is_throttled`
  - `test_settles_even_when_the_write_was_refused`
  - `test_repository_satisfies_the_port`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue tests/fakes tests/application/test_worker.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this backend (R17).
- The contract suite (R18).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R17 — queue-backend-selection

**Lane card.**

- **Depends on:** R01, R02, R16.
- **Wave:** 6.
- **Files touched:**
  - `src/vibey/bootstrap.py`
  - `src/vibey/bootstrap_interface.py`
  - `src/vibey/cli/main.py`
  - `src/vibey/domain/errors.py` (or `bootstrap.py`, beside `DatabaseNotConfigured`)
  - `tests/test_bootstrap.py`
  - `tests/cli/test_operational_commands.py` (new tests only)
- **Parallel-safe with:** the loop-service lanes, but not with R27 or R28, which share `bootstrap.py` and `cli/main.py`.
- **Must keep passing unchanged:**
  - `tests/cli/*`
  - `tests/test_bootstrap.py`
  - `tests/system/test_full_worker_faked.py`
  - `tests/infrastructure/test_operator_handlers.py`
  - the whole suite, which runs on the default `postgres` backend
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(queue): the composition root selects the queue backend

## Why
ADR-0044 §1: `[queue] backend` chooses the backend in `bootstrap.py`, the one
composition root, and nowhere else. Selecting `rabbitmq` without an AMQP URL fails
loudly, naming the fix. There is no silent fallback, for the same reason ADR-0002
gives for `DatabaseNotConfigured` (`bootstrap.py:641-662`).

The worker learns its prefetch from `-j` only after `build_app` has run
(`cli/main.py:1699`). The drain must also return buffered deliveries on SIGTERM
(ADR-0025, ADR-0026).

## Required behaviour
1. `class QueueBackendSettings` has
   `from_sources(config: VibeyConfig | None, environ: Mapping[str, str]) -> QueueBackendSettings`.
   Its fields are `backend`, `amqp_url`, `vhost`, `prefix` and `rabbitmq`
   (`QueueRabbitMqConfig`). Precedence is: `VIBEY_QUEUE_BACKEND` and
   `VIBEY_BUS_AMQP_URL` first, then `config.queue` and `config.bus`, then the R01
   defaults.
2. `class QueueBackendNotConfigured(VibeyError)`. Its message contains both remedies
   verbatim:
   - `export VIBEY_BUS_AMQP_URL=amqp://USER:PASS@HOST:5672/`
   - `export VIBEY_QUEUE_BACKEND=postgres`
3. `build_app`:
   - **postgres (the default):** everything as today. `wakeup` is R02's opener, and
     `queue_consumer` is a no-op `PostgresQueueConsumerControl`, whose `set_prefetch`
     and `drain` do nothing.
   - **rabbitmq:** with no `amqp_url`, raise `QueueBackendNotConfigured` before the
     pool is used. Otherwise build:
     - `AmqpClient(AmqpSettings(url))`, which connects lazily (R04);
     - `QueueNames(prefix)`, `RabbitMqJobTopology`, `WaitTierPlan`;
     - `DispatchingJobRecords(pool, writer=DispatchOutboxWriter())`;
     - `DispatchRelay`, `ProjectDeliveries`, `DispatchMissPolicy`;
     - `RabbitMqJobRepository` as `jobs`;
     - `PostgresHumanGateRepository(pool, dispatch_writer=DispatchOutboxWriter())` as
       `gates`;
     - a wakeup opener that returns `RabbitMqJobWakeup(deliveries)`;
     - `queue_consumer = RabbitMqQueueConsumerControl(deliveries)`, whose
       `set_prefetch(n)` calls `deliveries.set_prefetch(n)` and whose `drain()` calls
       `await jobs.stop()`.

     The AMQP client is closed in `build_app`'s `finally`.
4. `AppResources` gains `queue_consumer: QueueConsumerControlInterface`, declared in
   `bootstrap_interface.py`.
5. `vibey worker`:
   - After computing `count` (`cli/main.py:1699`), call
     `resources.queue_consumer.set_prefetch(count)`.
   - When the drive loops end, call `await resources.queue_consumer.drain()` in the
     existing `finally`, before closing the notifier.
6. With the default backend, nothing observable changes.

## Where to change
- `src/vibey/bootstrap.py` (`AppResources` `:134-171`, `build_app` `:694-916`).
- `src/vibey/bootstrap_interface.py`.
- `src/vibey/cli/main.py:1699-1760`.
- Put `QueueBackendSettings` and the two consumer-control classes in
  `src/vibey/infrastructure/queue/selection.py`, with their interfaces, so that
  `bootstrap.py` stays wiring.

## Acceptance criteria
- [ ] With no queue keys set, `build_app` yields `PostgresJobRepository`, and the whole existing suite passes unchanged.
- [ ] With `VIBEY_QUEUE_BACKEND=rabbitmq` and no URL, the start fails with `QueueBackendNotConfigured`, and its message holds both remedies.
- [ ] With the backend and a URL set, `build_app` yields `RabbitMqJobRepository`, and the gates carry a dispatch writer. No connection is made until first use.
- [ ] `vibey worker -j 3` calls `set_prefetch(3)`, and it calls `drain()` on exit.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/test_bootstrap.py`:
  - `test_default_backend_is_postgres`
  - `test_rabbitmq_without_url_names_both_remedies`
  - `test_rabbitmq_with_url_composes_the_rabbitmq_backend`
  - `test_env_beats_config_for_the_backend`
- `tests/infrastructure/queue/test_selection.py`:
  - `test_consumer_controls_forward_prefetch_and_drain`
  - `test_postgres_consumer_control_is_a_no_op`
- `tests/cli/test_operational_commands.py` (new tests):
  - `test_worker_sets_prefetch_to_its_parallelism`
  - `test_worker_drains_the_queue_consumer_on_exit`

  Use the existing notifier patch pattern from `:1255`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli tests/infrastructure/queue tests/system/test_full_worker_faked.py tests/infrastructure/test_operator_handlers.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Flipping the default (R34).
- The chart (R29–R31).
- Loop services.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R18 — queue-contract-suite

**Lane card.**

- **Depends on:** R17.
- **Wave:** 7.
- **Files touched:**
  - `tests/contracts/test_job_queue_contract.py` (new)
  - `tests/infrastructure/queue/test_rabbitmq_chaos.py` (new)
- **Parallel-safe with:** R27.
- **Must keep passing unchanged:**
  - `tests/contracts/test_rotation_cursor_contract.py`
  - `tests/infrastructure/db/test_chaos.py` (**protected; never edit it**)
  - all protected tests
- **Standing constraints:** see the header list.

## Title
test(queue): one contract suite and a chaos twin prove both queue backends

## Why
ADR-0044 §16. A port with two implementations is only a port if one suite binds both.
`tests/contracts/` already runs a contract against more than one implementation
(`tests/contracts/test_rotation_cursor_contract.py`).

The protected chaos test (`tests/infrastructure/db/test_chaos.py:49-170`) pins the
PostgreSQL backend's tally: zero double commits, zero lost jobs, every job terminal.
The RabbitMQ backend needs the same tally with **channels killed**, not tasks
abandoned. It goes in a new file, because the protected one is never edited.

## Required behaviour
1. In `tests/contracts/test_job_queue_contract.py`, a fixture `queue` is parametrized
   over three backends:
   - `"postgres"`: `PostgresJobRepository`;
   - `"rabbitmq-memory"`: `RabbitMqJobRepository` over Postgres and
     `InMemoryAmqpClient`, which always runs;
   - `"rabbitmq"`: a real broker, skipped unless `VIBEY_TEST_AMQP_URL` is set.

   Each yields a `QueueHarness` with `repo`, `gates` and an `async def settle()`
   helper. For the RabbitMQ backends, `settle()` runs the relay's drain and, on the
   memory broker, `expire()` of every wait tier. For PostgreSQL it does nothing.
2. The contract tests assert identical observable behaviour across all three
   backends:
   - enqueue is idempotent;
   - an empty queue claims `None`;
   - a dependency blocks the claim until it succeeds;
   - a future `run_after` blocks the claim;
   - `ack` is fenced (a second owner is refused);
   - `defer(retry_at=now)` makes the job claimable again after `settle()`;
   - `park` holds the job, and `answer` makes it claimable again;
   - an expired lease is claimable again after `reap()` (and, on RabbitMQ, after `settle()`);
   - `grant_attempts` widens and never narrows;
   - `count_unsettled` and `queue_depth` agree across backends for the same script.
3. `tests/infrastructure/queue/test_rabbitmq_chaos.py`
   (`@pytest.mark.slow @pytest.mark.integration`, real broker only):
   - 8 workers, each with its own `ProjectDeliveries` and channel;
   - 300 jobs with `max_attempts=1000`;
   - with probability 0.2 a worker "crashes": it closes its consumer channel without
     settling;
   - a concurrent `reap()` loop runs every 50 ms with `reconcile_interval_seconds=0`.

   The asserted tally has the same shape as `test_chaos.py:136-170`: executions equal
   commits plus refused, no double commit, no lost job, every job `succeeded`. It also
   prints the tally.

## Where to change
- The two new test files only. Reuse the fixtures from `tests/contracts/conftest.py`
  and `tests/infrastructure/queue/conftest.py`.

## Acceptance criteria
- [ ] The contract suite passes on `postgres` and `rabbitmq-memory` locally, and on all three in CI (R32).
- [ ] The chaos twin passes against a real broker.
- [ ] `git diff --stat develop -- tests/infrastructure/db/test_chaos.py` is empty.

## Tests to write first (TDD)
This lane is tests. Write the contract tests one by one against `postgres` first, then
enable the other parameters.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider tests/contracts tests/infrastructure/queue tests/infrastructure/db/test_chaos.py
    git diff --stat HEAD~1 -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- CI wiring (R32).
- Production code. If a contract test exposes a backend difference, stop and report
  which backend is wrong. Do not weaken the test.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R19 — run-protocol

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/domain/run_protocol.py` (new)
  - `src/vibey/domain/interfaces/run_protocol_interface.py` (new)
  - `src/vibey/domain/errors.py` (add one exception)
  - `tests/domain/test_run_protocol.py` (new)
- **Parallel-safe with:** every wave-1 lane. R06 also adds one exception to `errors.py`; the two additions merge trivially.
- **Must keep passing unchanged:**
  - `tests/domain/test_domain_purity.py`
  - `tests/domain/test_capacity.py`
  - `tests/domain/test_circuit.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(domain): the loop-service wire protocol

## Why
ADR-0044 §13. Callers publish run requests instead of spawning runners, and a
long-lived service per engine answers. The messages are a contract between two
processes, so they are pure, versioned and strictly decoded.

Two non-negotiables live in this contract:

- **No result carries a completion claim.** Completion stays the caller's judgement,
  checked after any capacity rejection (`build_implement_handler.py:241-263`).
- **No message carries a capacity field.** A credits exhaustion can never acquire a
  `resets_at` on the wire (the `CreditsExhausted` type at `domain/capacity.py:21-24`).

The service may run only its own binary with safe leading arguments. That argument
policy is pure too.

## Required behaviour
1. **Schema constants.** `vibey.run.request/1`, `vibey.run.accepted/1`,
   `vibey.run.progress/1`, `vibey.run.result/1`, `vibey.run.control/1`.
2. **Enums.**

   | enum | members (value) |
   |---|---|
   | `RunPurpose(StrEnum)` | `RUN` (`"run"`), `PROBE` (`"probe"`) |
   | `RunStatus(StrEnum)` | `EXITED`, `SUPERSEDED`, `ABANDONED`, `REJECTED`, `DEAD_LETTERED`, `DEADLINE_EXCEEDED`, each valued as its lower-case name |
   | `RunControlCommand(StrEnum)` | `STOP` (`"stop"`), `WIND_DOWN` (`"wind_down"`), `PROMPT_NOW` (`"prompt-now"`), `PROMPT_AT_BREAK` (`"prompt-at-break"`) |

3. **Messages.** All are frozen, slotted dataclasses, and every datetime must be
   timezone-aware.

   | dataclass | fields |
   |---|---|
   | `RunSupersede` | `key: str`, `attempt: int` (≥ 0) |
   | `RunRequest` | `run_id: UUID`, `engine_id: str`, `purpose: RunPurpose`, `args: tuple[str, ...]`, `cwd: str` (absolute), `run_dir: str \| None`, `supersedes: RunSupersede \| None`, `deadline_seconds: int` (≥ 1), `start_by: datetime`, `capture_output: bool`, `requested_at: datetime`, `caller: str` |
   | `RunAccepted` | `run_id`, `service_instance: str`, `pid: int \| None`, `started_at: datetime` |
   | `RunProgress` | `run_id`, `seq: int` (≥ 1), `line: str` |
   | `RunResult` | `run_id`, `status: RunStatus`, `exit_code: int \| None`, `meta_status: str \| None`, `started_at: datetime \| None`, `finished_at: datetime`, `detail: str`, `stdout: str \| None`, `stderr: str \| None` |
   | `RunControl` | `run_id`, `command: RunControlCommand`, `text: str \| None` |

   `RunResult` has **no** completion, success or capacity field.
4. **Codec.** `RunProtocolCodec` has `encode(message) -> dict[str, object]`, a
   `decode(raw) -> RunMessage` that dispatches on `schema` (where `RunMessage` is the
   union of the five message types), `to_bytes` and `from_bytes`. Decoding rejects an
   unknown schema, a missing key, **any extra key**, a wrong type and a naive datetime,
   raising the new `MalformedRunMessage(VibeyError)`. In particular a `resets_at`,
   `complete`, `success` or `capacity_state` key is rejected.
5. **Argument policy.** `RunArgsPolicy.reason(purpose, args) -> str | None` returns
   `None` when the arguments are allowed, and a human-readable reason otherwise.
   - For `RUN`, `args[0]` must be `run` or `resume`.
   - For `PROBE`, `args` must be exactly `("--version",)`, or `("run", "--help")`, or
     begin with `"doctor"`.
   - Empty `args`, or any argument containing `"\x00"`, is refused.
6. There is no clock, no I/O and no async anywhere in the module.

## Where to change
- `src/vibey/domain/run_protocol.py` and its interface
  (`RunProtocolCodecInterface`, `RunArgsPolicyInterface`).
- Copy R06's codec style.

## Acceptance criteria
- [ ] Hypothesis round trips hold for every message type.
- [ ] Every malformation is rejected, including each forbidden key.
- [ ] The encoded keys of `RunResult` are exactly the declared set.
- [ ] The argument policy table holds.
- [ ] 100% domain coverage; the purity test passes.

## Tests to write first (TDD)
- `tests/domain/test_run_protocol.py`:
  - `test_round_trip_properties` (Hypothesis, one per message type)
  - `test_decode_rejects_each_malformation`
  - `test_forbidden_keys_are_rejected` (parametrized over `resets_at`, `complete`, `success`, `capacity_state`)
  - `test_run_result_has_no_completion_or_capacity_field`
  - `test_args_policy_table`
  - `test_classes_satisfy_their_interfaces`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Any broker or process code.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R20 — run-dir-extraction

**Lane card.**

- **Depends on:** none.
- **Wave:** 1.
- **Files touched:**
  - `src/vibey/infrastructure/engines/run_dir.py` (new)
  - `src/vibey/infrastructure/engines/process_launcher.py` (new)
  - `src/vibey/infrastructure/engines/interfaces/{run_dir_interface,process_launcher_interface}.py` (new)
  - `src/vibey/infrastructure/engines/loop_process_adapter.py`
  - `tests/infrastructure/engines/{test_run_dir,test_process_launcher}.py` (new)
- **Parallel-safe with:** every wave-1 lane.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/test_loop_process_adapter.py`, all of it. It imports
    `_active_processes` and `_diagnostic_files` from the adapter module (`:23-24`), and
    it monkeypatches `module.asyncio.create_subprocess_exec` and `module.shutil.which`
    (`:1565-1566`).
  - `tests/infrastructure/test_gate_runner.py` and `tests/infrastructure/process/test_call_sites.py`,
    since `infrastructure/build/gate_runner.py:45` imports `isolate_python_env` from
    the adapter module.
  - `tests/application/test_conformance.py`
  - `tests/system/test_full_worker_faked.py`
  - `tests/live/**` (protected)
  - all protected tests
- **Standing constraints:** see the header list.

## Title
refactor(engines): extract the run-directory tailer, the inbox writer and the process launcher from LoopProcessAdapter

## Why
ADR-0044 §13. The loop service (R21, R22) and the caller-side `LoopServiceAdapter`
(R25) need exactly the machinery `LoopProcessAdapter` already has:

- launching an engine with the orchestrator's Python environment stripped and the
  local overlay applied (`loop_process_adapter.py:87-111`, `:160-192`, `:357-359`);
- tailing `events.jsonl` into `EngineEvent`s (`:418-589`);
- writing inbox commands (`:591-614`, `:653-657`);
- reading `stop-summary.md` (`:659-682`).

Duplicating it would break sub-doctrine 10.e inside this very repository. This lane
extracts those pieces into classes behind interfaces (9.b), and **the adapter's
behaviour does not change**.

## Required behaviour
1. `run_dir.py`:
   - `class RunDirTailer(descriptor: EngineDescriptor)`, with the method
     `async def tail(self, run_dir: Path, *, run_id: object, process_exited: Callable[[], bool]) -> AsyncIterator[EngineEvent]`.
     It is the body of `LoopProcessAdapter.tail` (`:425-589`) moved verbatim. The
     `_active_processes` exit check (`:567-580`) becomes the injected
     `process_exited()`, with the same one-poll grace.
   - `class RunInbox(run_dir: Path)`, with `write_prompt(text: str, *, now: bool) -> Path`
     (the body of `:593-614`), `write_stop() -> Path` (`:654-657`) and
     `write_command(command: str) -> Path`.
   - `class StopSummaryReader(descriptor)`, with
     `async def read(self, run_dir: Path, *, wait_seconds: float = 30.0) -> tuple[str, bool]`.
     It waits for the summary and returns `(summary, complete)`, with the logic of
     `:659-673`.
2. `process_launcher.py`: `class EngineProcessLauncher(descriptor, *, env_overlay, python_env)`
   with three methods:
   - `environment() -> dict[str, str]` (from `_engine_environment`, `:160-164`)
   - `async def spawn(self, *argv, env=None, stdout, stderr, cwd=None, start_new_session=False)`
     (from `_spawn`, `:166-192`)
   - `resolve(argv) -> tuple[str, ...]` (from `:357-359`)

   It calls `asyncio.create_subprocess_exec` and `shutil.which` **through the module
   attributes** (`asyncio.create_subprocess_exec(...)`, `shutil.which(...)`), never
   through `from asyncio import …`. That way the existing tests' monkeypatches of those
   globals still reach it.
3. `LoopProcessAdapter` delegates to these classes. `_active_processes`,
   `_diagnostic_files`, `_help_text_cache`, `isolate_python_env`, `ProcessError`,
   `_render_plan` and every public method **stay in `loop_process_adapter.py`**, with
   the same names and signatures. `__all__` is unchanged.
4. Behaviour is byte-identical: the same log event names, the same argv, the same
   environment, the same timeouts.

## Where to change
- `src/vibey/infrastructure/engines/loop_process_adapter.py` and the two new modules.
- The interfaces go in `infrastructure/engines/interfaces/`, a package already listed
  in `.importlinter:98-120`.

## Acceptance criteria
- [ ] `tests/infrastructure/engines/test_loop_process_adapter.py` passes **with no edits**.
- [ ] The live, protected and conformance tests pass.
- [ ] The new classes have direct unit tests.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/engines/test_run_dir.py`:
  - `test_tailer_translates_and_stops_on_terminal_meta`
  - `test_tailer_stops_after_process_exits_without_status`
  - `test_inbox_writes_prompt_stop_and_command_files`
  - `test_stop_summary_reader_waits_and_detects_the_marker`
- `tests/infrastructure/engines/test_process_launcher.py`:
  - `test_environment_strips_the_orchestrator_venv_and_applies_the_overlay`
  - `test_resolve_uses_an_absolute_binary_path`
  - `test_spawn_merges_the_overlay_last`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/engines tests/infrastructure/test_gate_runner.py tests/infrastructure/process tests/application/test_conformance.py tests/system/test_full_worker_faked.py tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/infrastructure/engines/test_loop_process_adapter.py tests/live

## Out of scope
- Any service or queue code.
- Changing any behaviour.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R21 — local-run-executor

**Lane card.**

- **Depends on:** R19, R20.
- **Wave:** 2.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/__init__.py` (new)
  - `src/vibey/infrastructure/loop_service/{local_run_executor,result_store}.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/{__init__,local_run_executor_interface,result_store_interface}.py` (new)
  - `.importlinter`
  - `tests/infrastructure/loop_service/{__init__,test_local_run_executor,test_result_store}.py` (new)
- **Parallel-safe with:** R04, R07, R10 and R29. It precedes R12 in the `.importlinter` chain.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/*`
  - `tests/infrastructure/process/*`
  - `tests/meta/test_import_contracts_bind.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(loop-service): run one request as a local engine subprocess and persist its result

## Why
ADR-0044 §13. The loop service runs each request **as the runner's own CLI in a
subprocess**, with the same argv, run directory, inbox and exit codes as today. The
protected live conformance suite therefore keeps pinning what runs.

The service also persists each result beside the diagnostics `LoopProcessAdapter`
already writes (`loop_process_adapter.py:365-368`), before it acknowledges the
request. That is what makes a redelivered request idempotent.

It must run only its own binary, only under a configured root, and with only the
arguments `RunArgsPolicy` allows (R19). This is the security boundary the ADR names.

## Required behaviour
1. `class RunResultStore`:
   - `path(cwd: str, run_id: UUID) -> Path` returns
     `Path(cwd)/.vibey/diagnostics/<run_id>.result.json`.
   - `write(cwd, result: RunResult) -> None` writes atomically (a temp file plus
     `os.replace`) using `RunProtocolCodec`.
   - `read(cwd, run_id) -> RunResult | None` returns `None` when the file is missing,
     and `None` with a `warning` log when it is malformed.
2. `class LocalRunExecutor(binary: str, launcher: EngineProcessLauncherInterface, reaper: ProcessReaperInterface, root: Path)`:
   - `reason_to_reject(request: RunRequest) -> str | None` combines
     `RunArgsPolicy.reason`, `cwd` being absolute and `Path(cwd).resolve()` lying under
     `root.resolve()`, and `run_dir` (when given) lying under `cwd`.
   - `async def start(self, request) -> LocalRunInterface`:
     - Resolve `(binary, *request.args)` through the launcher.
     - For `purpose=RUN` without `capture_output`, stdout and stderr go to
       `<cwd>/.vibey/diagnostics/<run_id>.stdout` and `.stderr`. Otherwise they are
       pipes, keeping the last 64 KiB of each.
     - Spawn with `cwd=request.cwd` and `start_new_session=True`.
3. `class LocalRun`:
   - `pid`
   - `async def wait(self, timeout: float | None) -> int | None`: the exit code, or
     `None` on a timeout
   - `async def stop(self, grace_seconds: float) -> None`: when there is a `run_dir`,
     call `RunInbox(run_dir).write_stop()`; wait `grace_seconds`; if the process is
     still alive, call `reaper.kill_and_reap(process)`
   - `control(command: RunControlCommand, text: str | None) -> None`: map
     `STOP`/`WIND_DOWN` to `RunInbox.write_command(command.value)` and the two prompt
     commands to `write_prompt`
   - `output() -> tuple[str | None, str | None]`
   - `meta_status() -> str | None`: `run_dir/meta.json`'s `status`, or `None`
4. `.importlinter`: `vibey.infrastructure.loop_service.interfaces` joins the
   `infrastructure-interfaces-declare-only` contract's `source_modules`.

## Where to change
- The new package. Use R20's `EngineProcessLauncher` and `RunInbox`, and the existing
  `ProcessReaper` (`infrastructure/process/reaper.py`).

## Acceptance criteria
- [ ] A scripted fake engine is written into a temp directory on `PATH`, like the
  existing adapter tests (`test_loop_process_adapter.py:389-420`). It runs, its exit
  code comes back, its stdout lands in the diagnostics file, and `meta_status` reads
  its `meta.json`.
- [ ] `stop` writes the inbox stop and kills the process after the grace period.
- [ ] Each rejection reason fires: arguments, a `cwd` outside the root, a relative
  `cwd`, and a `run_dir` outside `cwd`.
- [ ] The result store round-trips, writes atomically, and returns `None` for a
  missing or malformed file.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_local_run_executor.py`:
  - `test_runs_the_fake_engine_and_returns_its_exit_code`
  - `test_run_output_goes_to_the_diagnostics_files`
  - `test_probe_output_is_captured_and_capped`
  - `test_stop_writes_the_inbox_then_kills_after_grace`
  - `test_control_maps_commands_to_inbox_files`
  - `test_rejects_each_unsafe_request`
- `tests/infrastructure/loop_service/test_result_store.py`:
  - `test_round_trip`
  - `test_write_is_atomic`
  - `test_missing_and_malformed_read_none`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/meta/test_import_contracts_bind.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- AMQP (R22–R24).
- CLI (R27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R22 — loop-service-host

**Lane card.**

- **Depends on:** R04, R21.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/host.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/host_interface.py` (new)
  - `tests/infrastructure/loop_service/test_host.py` (new)
- **Parallel-safe with:** R11, R12, R15 and R24. R23 extends `host.py` after it.
- **Must keep passing unchanged:**
  - R21 tests
  - the `vibey_bootstrap` amqp tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(loop-service): the service host consumes run requests, dedupes, supersedes, replies and acknowledges

## Why
ADR-0044 §13. One long-lived process per engine consumes `vibey.runs.<engine_id>`
with a configured prefetch, so that one loaded model is shared in an orderly way. The
host owns four of the invariants the ADR calls the riskiest:

1. A redelivered request never starts a second process.
2. A result is persisted and published before its request is acknowledged.
3. A request that is superseded, or not started in time, is answered rather than run.
4. No two runs ever share one worktree.

## Required behaviour
1. `class LoopServiceHost` is constructed with:
   - `engine_id: str`
   - `client: AmqpClientInterface`
   - `names: QueueNamesInterface`
   - `executor: LocalRunExecutorInterface`
   - `results: RunResultStoreInterface`
   - `settings: LoopServiceConfigInterface`
   - `delivery_limit: int = 3`
   - `consumer_timeout_seconds: int = 21600`
   - `clock: Clock`
   - `instance_id: str`
   - `logger: Logger`
2. `async def start(self)`:
   - Declare `names.runs_exchange()` (direct) and `names.run_dead_exchange()` (direct).
   - Declare the queue `names.run_queue(engine_id)` with
     `{"x-queue-type":"quorum","x-delivery-limit":delivery_limit,"x-dead-letter-exchange":names.run_dead_exchange(),"x-dead-letter-strategy":"at-least-once","x-overflow":"reject-publish","x-consumer-timeout":consumer_timeout_seconds*1000}`,
     bound with key `engine_id`.
   - Declare `names.run_dead_queue(engine_id)`, bound on the dead exchange with key
     `engine_id`.
   - Consume the run queue with `prefetch=settings.prefetch` and the handler
     `_on_request`.
3. `_on_request(delivery)` checks, in order:
   - **a.** Decode the body. A `MalformedRunMessage`, or a message that is not a
     `RunRequest` or not for this engine, is sent to `dead_letter()`.
   - **b.** The `run_id` is already active in this instance (a redelivery after a
     channel blip): rebind the active run's delivery to this one, and do not start
     anything. vibey_bootstrap's `ReplayGuard` (`servicebus/async_ext.py:26-49`)
     records the run ids seen, for logging.
   - **c.** `results.read(cwd, run_id)` exists: republish that result to `reply_to`,
     then `complete()`.
   - **d.** `run_dir` is given, it exists, and its `meta.json` status is not
     `finished`, `failed` or `stopped`: this is a crashed earlier start. Write, publish
     and complete a result with status `ABANDONED` and detail `"run directory left non-terminal by a previous service instance"`.
   - **e.** `clock.now() > request.start_by`: reply `REJECTED` with
     `"not started before start_by"`, then complete.
   - **f.** `executor.reason_to_reject(request)` is not `None`: reply `REJECTED` with
     that reason, then complete.
   - **g.** An active run on the same `cwd`:
     - with the same `supersedes.key` and a lower `attempt`: call
       `stop(settings.supersede_grace_seconds)` on it, then write, publish and
       complete **its** result as `SUPERSEDED`;
     - with any other key, or none: reply `REJECTED` with `"worktree busy"` and
       complete, without running.
   - **h.** Otherwise start the run:
     - Publish `RunAccepted`.
     - While it runs, publish one `RunProgress` per new `events.jsonl` line, when
       `settings.publish_progress` is on and there is a `run_dir`. Poll every 0.5 s,
       with `seq` starting at 1.
     - Wait for the exit, bounded by `deadline_seconds`. Past the deadline, stop with
       the grace, and the status is `DEADLINE_EXCEEDED`; otherwise it is `EXITED`,
       with `exit_code` and `meta_status`.
     - Write the result through `results.write` (purpose `RUN` only), publish it with
       a confirm, then `complete()` the delivery.
4. Replies go to the default exchange (`""`) with routing key `request.reply_to` and
   `correlation_id = str(run_id)`. A request without `reply_to` is still run and
   persisted, and its replies are skipped.
5. `async def stop(self)` is the drain. It cancels the consumer and lets active runs
   finish for up to `grace_seconds`. It then stops the runs still going; each one's
   result is `ABANDONED`, written, published and completed.
6. The host calls `record_consumer_iteration()` and `record_message_settled()` through
   the amqp client. It never interprets capacity and never reads events for meaning.

## Where to change
- The new module and its interface.

## Acceptance criteria
- [ ] All tests use `InMemoryAmqpClient` and the R21 fake engine script.
- [ ] Each rule 3a–3h has a test. Rule b must show that no second process started.
- [ ] Every completed delivery happened after its result was persisted and published.
- [ ] The drain abandons in-flight runs after the grace period.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_host.py`:
  - `test_runs_a_request_and_replies_accepted_progress_result`
  - `test_malformed_request_is_dead_lettered`
  - `test_redelivery_of_an_active_run_starts_nothing`
  - `test_persisted_result_is_republished_not_rerun`
  - `test_non_terminal_run_dir_is_abandoned`
  - `test_late_request_is_rejected`
  - `test_unsafe_request_is_rejected`
  - `test_higher_attempt_supersedes_the_older_run`
  - `test_different_key_on_a_busy_worktree_is_rejected`
  - `test_deadline_stops_the_run`
  - `test_result_is_persisted_before_ack`
  - `test_drain_abandons_after_grace`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The control, probe and dead-letter consumers (R23).
- The CLI (R27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R23 — loop-service-control

**Lane card.**

- **Depends on:** R22.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/control.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/control_interface.py` (new)
  - `src/vibey/infrastructure/loop_service/host.py` (wire-up only)
  - `tests/infrastructure/loop_service/test_control.py` (new)
- **Parallel-safe with:** R13, R14, R25 and R26.
- **Must keep passing unchanged:**
  - R22 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(loop-service): control messages, preflight probes and dead-letter replies

## Why
ADR-0044 §13 gives the service three more consumers:

- **Control.** A caller's stop, wind-down or prompt must reach the runner's own inbox
  (`loop_process_adapter.py:591-614`, `:651-658`), whichever replica runs it.
- **Probes.** `--version`, `doctor` and `run --help` must run in the service's
  environment, which is where auth matters. They must not queue behind an hour-long
  run at prefetch 1. Conformance reads `help_text` from them (`application/conformance.py:119`).
- **Dead-letter replies.** A request that dead-letters after crashing its service
  must still be answered, so its caller does not wait for a result that will never
  come.

## Required behaviour
1. `class RunControlConsumer(host, client, names, engine_id)`. `start()` declares a
   server-named, exclusive, auto-delete queue bound to `names.control_exchange()`
   (declared as topic) with key `engine_id`, and consumes it (prefetch 16). Each
   `RunControl` addressed to a run that is active in this host is passed to
   `LocalRun.control(command, text)`. Unknown runs are ignored. Every delivery is
   completed, and a malformed one is completed and logged.
2. `class RunProbeConsumer(executor, client, names, engine_id, clock)`. `start()`
   declares `names.probe_queue(engine_id)`, a classic, non-exclusive queue bound on the
   runs exchange with `names.probe_key(engine_id)`, and consumes it with prefetch 4.
   Each probe `RunRequest` is checked by `executor.reason_to_reject`, run with
   `capture_output`, bounded by `deadline_seconds`, and answered with a `RunResult`
   carrying its `stdout` and `stderr`. Probe results are not persisted.
3. `class RunDeadLetterReplier(client, names, engine_id)`. `start()` consumes
   `names.run_dead_queue(engine_id)`. For each request that has a `reply_to`, it
   publishes `RunResult(status=DEAD_LETTERED, detail="the request crashed its service <delivery_count> times")`,
   then completes the delivery.
4. `LoopServiceHost.start()` also starts these three consumers, and `stop()` cancels
   them.

## Where to change
- The new `control.py`, its interface, and `host.py`'s `start` and `stop`.

## Acceptance criteria
- [ ] A control `STOP` reaches the active run's inbox.
- [ ] A probe `--version` answers with the fake engine's stdout, even while a long run occupies the prefetch-1 run consumer.
- [ ] A dead-lettered request gets a `DEAD_LETTERED` reply.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_control.py`:
  - `test_stop_reaches_the_active_runs_inbox`
  - `test_prompts_reach_the_inbox`
  - `test_control_for_an_unknown_run_is_ignored`
  - `test_probe_runs_beside_a_long_run`
  - `test_unsafe_probe_is_rejected`
  - `test_dead_lettered_request_is_answered`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The caller side (R24–R26).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R24 — loop-service-client

**Lane card.**

- **Depends on:** R04, R19.
- **Wave:** 3.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/client.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/client_interface.py` (new)
  - `tests/infrastructure/loop_service/test_client.py` (new)
- **Parallel-safe with:** R11, R12, R15 and R22. It shares `loop_service/interfaces/__init__.py`, which stays docstring-only.
- **Must keep passing unchanged:**
  - R21 tests
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(loop-service): the caller's client submits runs and receives their replies

## Why
ADR-0044 §13. Workers, `vibey work` and `vibey design`, the storms and the operator's
kickoff all publish run requests instead of spawning runners. Their replies come to
one exclusive reply queue per caller process, correlated by `run_id`. This lane is the
single client all of those callers share, so sub-doctrine 10.e holds inside vibey too.

## Required behaviour
1. `class LoopServiceClient(client: AmqpClientInterface, names, clock, caller: str)`.
2. `async def start(self)` declares a server-named, exclusive, auto-delete reply
   queue and consumes it with prefetch 64. Each reply is routed by its
   `correlation_id` to the `RunTicket` for that run; unknown ids are completed and
   dropped. It runs once, and the methods below start it lazily.
3. `async def submit(self, request: RunRequest) -> RunTicket` publishes to
   `names.runs_exchange()` with key `request.engine_id` for `RUN`, or
   `names.probe_key(engine_id)` for `PROBE`. The properties are
   `message_id = correlation_id = str(run_id)`, `reply_to = <reply queue>` and
   `type="run.request"`. There is **no expiration**.
4. `class RunTicket`:
   - `async def accepted(self, timeout: timedelta) -> RunAccepted | None`
   - `async def progress(self) -> AsyncIterator[RunProgress]`, which ends when the
     result arrives
   - `async def result(self, timeout: timedelta | None) -> RunResult | None`
   - `latest_result -> RunResult | None`
5. `async def control(self, engine_id: str, message: RunControl) -> None` publishes to
   `names.control_exchange()`, a topic exchange the client declares idempotently, with
   key `engine_id`.
6. `async def probe(self, engine_id, args, *, cwd, timeout) -> RunResult | None`
   builds a `PROBE` request and submits it. It sets
   `start_by = now + timeout`, `deadline_seconds = ceil(timeout)` and
   `capture_output = True`, and awaits the result.
7. `async def close(self)` cancels the reply consumer.

## Where to change
- The new module and its interface.

## Acceptance criteria
- [ ] Tests use the in-memory client with a stub responder that consumes the run queue and replies.
- [ ] Submit, accepted, progress and result are routed per run.
- [ ] Two concurrent runs never cross their replies.
- [ ] A probe round-trips.
- [ ] A control message reaches the control exchange.
- [ ] Timeouts return `None`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_client.py`:
  - `test_submit_routes_by_purpose`
  - `test_replies_are_routed_by_correlation_id`
  - `test_concurrent_runs_do_not_cross`
  - `test_progress_ends_with_the_result`
  - `test_probe_round_trip`
  - `test_control_is_published_to_the_engine_key`
  - `test_timeouts_return_none`
  - `test_unknown_reply_is_dropped`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The engine adapter (R25).
- The command executor (R26).
- The CLI (R27).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R25 — loop-service-adapter

**Lane card.**

- **Depends on:** R20, R24.
- **Wave:** 4.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/adapter.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/adapter_interface.py` (new)
  - `src/vibey/application/dto.py` (`RunSpec`: two defaulted fields)
  - `src/vibey/application/worker.py` (one new exception, caught beside `CapacityDeferred`)
  - `src/vibey/application/build_implement_handler.py` (`:222-230`: pass the two fields)
  - `tests/infrastructure/loop_service/test_adapter.py` (new)
  - `tests/application/test_worker.py` (new test only)
  - `tests/application/test_build_implement_handler.py` (new test only)
- **Parallel-safe with:** R13, R14, R23 and R26. Note that R26 also imports the new exception.
- **Must keep passing unchanged:**
  - every existing test in `tests/application/test_worker.py` and `tests/application/test_build_implement_handler.py`
  - `tests/fakes/test_port_parity.py`
  - `tests/system/*`
  - `tests/live/**`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(engines): LoopServiceAdapter publishes a run instead of spawning one

## Why
ADR-0044 §13. The engine seam `EngineAdapter` (`application/interfaces/engines.py:44-80`)
does not change. A second implementation publishes to the engine's loop service.

Its evidence path stays exactly today's: it tails `events.jsonl` on the shared volume
through R20's `RunDirTailer`. So `run_and_record` (`build_engine_run.py:70-159`) and
the order it checks capacity before completion (`build_implement_handler.py:241-263`)
are untouched.

Two new facts need small application changes:

- **A run's supersede identity comes from its job.** `RunSpec` gains `supersede_key`
  and `attempt`.
- **A saturated engine queue is not an engine capacity signal.** It must defer
  without opening a circuit (`application/interfaces/queue.py:40-57`), so the worker
  gets an `EngineQueueSaturated` beside `CapacityDeferred` (`worker.py:46-57`,
  `:159-165`).

## Required behaviour
1. `RunSpec` (`application/dto.py:110-119`) gains `supersede_key: str | None = None`
   and `attempt: int = 0`, both at the end, so every existing constructor call still
   works.
2. `build_implement_handler.py:222-230` passes `supersede_key=str(job.id)` and
   `attempt=job.attempts`.
3. `application/worker.py` adds `class EngineQueueSaturated(Exception)` with
   `retry_at` and `detail`. `run_once` catches it beside `CapacityDeferred` and
   produces `Defer(exc.retry_at, exc.detail, capacity=False)`.
4. `class LoopServiceAdapter(descriptor: EngineDescriptor, client: LoopServiceClientInterface, *, clock, run_queue_wait: timedelta, deadline: timedelta, root_hint: str | None = None)`
   implements `EngineAdapter`:
   - **`start(spec)`:**
     - Write the plan to `spec.worktree_path/.vibey/plans/<run_id>.md`, using
       `_render_plan` exactly as `loop_process_adapter.py:341-346` does.
     - Set `args = build_argv(descriptor, spec)[1:]` (`argv.py:10-30`) and
       `run_dir = worktree/<state_dir>/runs/<run_id>`.
     - Submit a `RunRequest(purpose=RUN, cwd=str(worktree_path), supersedes=RunSupersede(spec.supersede_key, spec.attempt) if spec.supersede_key else None, start_by=now+run_queue_wait, deadline_seconds=deadline, capture_output=False, …)`.
     - Await `ticket.accepted(run_queue_wait + 5 s)`. If it is `None`, or the result
       is `REJECTED` with `"worktree busy"` or `"not started before start_by"`, raise
       `EngineQueueSaturated(retry_at=now+run_queue_wait, detail=...)`.
     - Otherwise return `RunHandle(run_id, engine_id, run_dir, pid=accepted.pid)`.
   - **`tail(handle)`:** `RunDirTailer.tail(run_dir, run_id=…, process_exited=lambda: ticket.latest_result is not None)`.
   - **`run_exit_code(handle)`:** `ticket.latest_result.exit_code`, else
     `RunResultStore.read(cwd, run_id).exit_code`, else `None`.
   - **`diagnostic_tail(handle)`:** the tail of the diagnostics stdout and stderr
     files, as `loop_process_adapter.py:625-642` does. `release_diagnostics` is a
     no-op.
   - **`send_prompt`:** publishes `RunControl(PROMPT_NOW or PROMPT_AT_BREAK)`.
   - **`stop(handle)`:** publishes `RunControl(STOP)`, then builds `StopSummary` from
     `StopSummaryReader` and `snapshot()` as `:659-706` does, with no process
     handling.
   - **`snapshot`:** as in `:708-727`.
   - **`preflight()`:** probes `("--version",)` and `("doctor", *descriptor.doctor_args)`,
     and caches `("run", "--help")` output for `help_text`, all through
     `client.probe(timeout=descriptor-appropriate: 10 s, doctor 120 s)`. A probe with
     no answer gives `PreflightResult(installed=False, …, detail="no loop service answered for <engine>")`.
   - **`help_text`:** a sync property returning the cached text, or `None` before the
     first `preflight()`.
   - **`classify` and `attribute`:** from `classify.py`, unchanged.

## Where to change
- The new module, plus the three application files named on the card.

## Acceptance criteria
- [ ] Every scenario uses the in-memory client and R24's stub responder, which writes `events.jsonl` and `meta.json` into a temp worktree.
- [ ] `run_and_record` sees the same events and exit code as it would from a subprocess.
- [ ] Exit 75 reaches the wind-down path.
- [ ] A capacity-rejection event still outranks a completion verdict.
- [ ] Queue saturation becomes `Defer(capacity=False)` in `WorkerLoop`, and no circuit opens.
- [ ] Preflight and `help_text` come from probes.
- [ ] No existing test needed an edit.
- [ ] 100% coverage on `application/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_adapter.py`:
  - `test_start_writes_the_plan_and_submits_the_same_argv`
  - `test_tail_reads_run_dir_events_until_the_result`
  - `test_exit_code_from_the_result_or_the_persisted_file`
  - `test_wind_down_exit_75_reaches_the_handler`
  - `test_capacity_event_outranks_completion`
  - `test_unaccepted_run_raises_queue_saturated`
  - `test_busy_worktree_raises_queue_saturated`
  - `test_stop_sends_control_and_reads_the_summary`
  - `test_preflight_and_help_text_come_from_probes`
  - `test_adapter_satisfies_engine_adapter`
- `tests/application/test_worker.py`: `test_queue_saturation_defers_without_capacity`
- `tests/application/test_build_implement_handler.py`: `test_run_spec_carries_job_identity`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/application tests/fakes tests/system tests/live
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this adapter (R28).
- The DESIGN executor (R26).
- Docs and CHANGELOG.

**Stop rule:** if an existing test compares whole `RunSpec` values and fails because
of the new fields, stop and report.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R26 — loop-service-executor

**Lane card.**

- **Depends on:** R24, and R25 (for `EngineQueueSaturated`).
- **Wave:** 5.
- **Files touched:**
  - `src/vibey/infrastructure/loop_service/command_executor.py` (new)
  - `src/vibey/infrastructure/loop_service/interfaces/command_executor_interface.py` (new)
  - `tests/infrastructure/loop_service/test_command_executor.py` (new)
- **Parallel-safe with:** R13, R14 and R23.
- **Must keep passing unchanged:**
  - `tests/infrastructure/engines/test_claudeloop_process.py`
  - `tests/infrastructure/engines/test_opencodeloop_process.py`
  - `tests/cli/test_sovereign_provider_options.py`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(loop-service): DESIGN and DECOMPOSE runs go through the loop service too

## Why
ADR-0044 §13. The DESIGN and DECOMPOSE providers do not use `EngineAdapter`. They
spawn through an injected `CommandExecutor` that returns `CommandResult(returncode, stdout, stderr)`
(`claudeloop_process.py:28-47` and `:88-104`, `opencodeloop_process.py:26-45` and
`:79-85`).

"Callers publish run jobs instead of spawning runner subprocesses" covers these runs
as well. A service-backed `CommandExecutor` keeps both providers unchanged.

## Required behaviour
1. `class LoopServiceCommandExecutor(engine_id: str, binary: str, client: LoopServiceClientInterface, *, clock, run_queue_wait: timedelta, deadline: timedelta)`
   implements `vibey.infrastructure.interfaces.CommandExecutor`.
2. `async def execute(self, argv: tuple[str, ...]) -> CommandResult`:
   - `argv[0]`'s basename must equal `binary`, else `ValueError`.
   - The run id is the value after `--run-id` in `argv`, else a new `uuid4`.
   - The cwd is the value after `--cwd`, else `ValueError("the loop service needs --cwd in argv")`.
   - Submit `RunRequest(purpose=RUN, args=argv[1:], cwd=…, run_dir=None, supersedes=None, capture_output=True, start_by=now+run_queue_wait, deadline_seconds=…)`.
   - An unaccepted request, or a result `REJECTED` for `worktree busy` or lateness,
     raises `EngineQueueSaturated` (R25).
   - Otherwise return `CommandResult(result.exit_code if it is not None else 1, result.stdout or "", result.stderr or "")`.
3. Capacity detection stays where it is today, in each provider's own parsing of the
   run directory and stderr (`claudeloop_process.py:148-172`). The executor adds none.

## Where to change
- The new module and its interface. The `CommandExecutor` Protocol is in
  `src/vibey/infrastructure/interfaces/`.

## Acceptance criteria
- [ ] With the in-memory client and a stub responder, `ClaudeLoopProcess(executor=LoopServiceCommandExecutor(...))` produces the same `ClaudeLoopResult` as it does with `AsyncSubprocessExecutor`, for the same scripted run directory and stderr.
- [ ] A missing `--cwd` or a wrong binary raises.
- [ ] Saturation raises `EngineQueueSaturated`.
- [ ] 100% infrastructure coverage.

## Tests to write first (TDD)
- `tests/infrastructure/loop_service/test_command_executor.py`:
  - `test_execute_round_trips_returncode_stdout_stderr`
  - `test_claudeloop_process_runs_unchanged_over_the_service`
  - `test_opencodeloop_process_runs_unchanged_over_the_service`
  - `test_missing_cwd_and_wrong_binary_raise`
  - `test_saturation_raises`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/loop_service tests/infrastructure/engines tests/cli/test_sovereign_provider_options.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Selecting this executor in the CLI (R28).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R27 — loop-service-cli

**Lane card.**

- **Depends on:** R17, R23, R24. R25 is needed for `loop submit`: merge it first.
- **Wave:** 7.
- **Files touched:**
  - `src/vibey/cli/loop_service.py` (new)
  - `src/vibey/cli/main.py` (registration only)
  - `src/vibey/bootstrap.py` (`build_loop_service`, `build_loop_client`)
  - `src/vibey/infrastructure/loop_service/residency.py` (new, + interface)
  - `tests/cli/test_loop_service_cli.py` (new)
  - `tests/infrastructure/loop_service/test_residency.py` (new)
- **Parallel-safe with:** R18.
- **Must keep passing unchanged:**
  - `tests/cli/*`
  - `tests/test_bootstrap.py`
  - the image contract "every console script is on PATH" (`ci.yml:822`); no console script is added
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(cli): vibey loop-service runs one engine's service, and vibey loop submit publishes a run

## Why
ADR-0044 §13 asks for one long-lived service per engine. That needs an entry point the
chart can run (R30), and one a laptop can run in a terminal. Storms and humans need a
way to publish a run and follow it without spawning the runner: QwenStorm's
`storm-queue.sh` serializes lanes by hand today, and the engine queue should do that.

The qwenloop service must also keep one model resident:

- With an attached endpoint (`QWENLOOP_BASE_URL`, derived from `VIBEY_OLLAMA_URL` by
  `local_engines.py:158-188`), Ollama already keeps it.
- Otherwise the service runs `qwenloop server start` once
  (`qwenloop/cli/app.py:638-660`), so that every run attaches to that healthy server
  (`app.py:269-271`).

The service needs no database. Only the broker and the filesystem are required.

## Required behaviour
1. `bootstrap.py`:
   - `build_loop_service(engine_id: EngineId, *, config: VibeyConfig | None, environ) -> LoopServiceHost`.
     It resolves the binary from `BY_ENGINE_ID` (claudeloop-local uses the claudeloop
     binary), the environment overlay from `LocalEndpointEnvironment(environ).overlay_for(engine_id)`,
     the AMQP URL and prefix from R17's `QueueBackendSettings`, the root from
     `config.loop_services.root`, and the settings from
     `config.loop_services.for_engine(engine_id)`.
   - `build_loop_client(...) -> LoopServiceClient`.
   - With no AMQP URL, both raise `QueueBackendNotConfigured` (R17).
2. `class ModelResidency(engine_id, launcher, environ)` has
   `async def ensure(self) -> str`, which returns a human-readable line:
   - for engines other than `qwenloop`: `"n/a"`;
   - when `QWENLOOP_BASE_URL` is set, after the overlay: `"attached: <url>"`;
   - otherwise it runs `qwenloop server start` through the launcher, bounded by
     600 s, and returns `"managed server started"`, or `"managed server start failed: <tail>"`.
     A failure is a warning, not an exit, because each run can still start its own
     server.
3. `vibey loop-service --engine ID [--prefetch N]`, in the new `cli/loop_service.py`,
   registered in `main.py` the way `ledger_search` is (`main.py:39`, `:88-89`):
   - It builds the host and prints `loop-service started: engine=<id> prefetch=<n> residency=<line>`.
   - It installs the asyncio SIGTERM handler and releases the early latch, copying
     `cli/main.py:1519-1540`.
   - It runs until SIGTERM, then calls `host.stop()` and exits 0.
   - `--prefetch` overrides the config.
   - A missing AMQP URL exits 2 with R17's message.
4. `vibey loop submit --engine ID --plan FILE --cwd DIR [--run-id UUID] [--effort standard] [--isolation worktree] [--follow] [--timeout SECONDS]`:
   - It builds a `LoopServiceAdapter` (R25) for the engine's descriptor and calls
     `start(RunSpec(...))`.
   - With `--follow` it prints each progress line.
   - It awaits the result for up to `--timeout`, prints the `RunResult` as one JSON
     line, and exits with the run's exit code, or 1 when there is none. Saturation
     exits 75, the family's "hand over" code.

## Where to change
- The new CLI module and residency module, `bootstrap.py`, and `main.py` for
  registration.

## Acceptance criteria
- [ ] Using `CliRunner`, and the in-memory client injected through `build_loop_service`'s seam, `vibey loop-service` starts and drains on a simulated SIGTERM.
- [ ] `vibey loop submit` against a stub responder prints the result JSON and returns its exit code.
- [ ] A missing URL exits 2 with both remedies.
- [ ] Residency covers attached, managed-ok, managed-fail and non-qwenloop.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/cli/test_loop_service_cli.py`:
  - `test_loop_service_starts_and_drains`
  - `test_loop_service_without_amqp_url_exits_2`
  - `test_prefetch_flag_overrides_config`
  - `test_loop_submit_prints_the_result_and_returns_its_exit_code`
  - `test_loop_submit_follow_prints_progress`
  - `test_loop_submit_saturated_exits_75`
- `tests/infrastructure/loop_service/test_residency.py`:
  - `test_attached_endpoint_needs_nothing`
  - `test_managed_server_is_started_once`
  - `test_start_failure_is_a_warning`
  - `test_other_engines_are_na`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli tests/test_bootstrap.py tests/infrastructure/loop_service
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Switching the worker to service invocation (R28).
- The chart (R30).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R28 — invocation-selection

**Lane card.**

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
See STORM/SPEC-TEMPLATE.md.

---

# Lane R29 — chart-broker-core

**Lane card.**

- **Depends on:** R01, for the environment variable names.
- **Wave:** 2.
- **Files touched:**
  - `deploy/helm/vibey/templates/broker.yaml` (new)
  - `deploy/helm/vibey/templates/surfaces.yaml` (remove the moved objects; keep the bus `VibeySurface`)
  - `deploy/helm/vibey/templates/plane.yaml` (one condition)
  - `deploy/helm/vibey/templates/worker.yaml`
  - `deploy/helm/vibey/values.yaml`
  - `deploy/helm/golden/{default,ollama,ollama-gpu-qwenloop,surfaces-off}.yaml` (regenerated)
  - `tests/infrastructure/test_chart_broker_golden.py` (new)
- **Parallel-safe with:** every non-chart lane. It starts the chart chain (R29 → R30 → R31 → R34).
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_keda_scaler_query.py` (the `keda-*` goldens must not change)
  - the chart job's golden check for `keda-latest` and `keda-project`
  - cluster-smoke's deployment list (`ci.yml:904-935`); the name `vibey-vibey-rabbitmq` is unchanged
  - all protected tests
- **Standing constraints:** see the header list. `helm` must be v4.2.4, the version the `chart` job pins (`ci.yml:862-866`). If it is not on `PATH`, stop and report. Never hand-edit a golden.

## Title
feat(chart): the RabbitMQ broker is core infrastructure

## Why
ADR-0044 §15. RabbitMQ is only rendered inside the surfaces block
(`deploy/helm/vibey/templates/surfaces.yaml:99-215`, gated by `surfaces.enabled` at
`:1`). A queue and loop services that depend on it must work even with
`surfaces.enabled=false`.

Sub-doctrine 12.c forbids making anything less configurable. So:

- the broker's settings stay at `surfaces.rabbitmq.*` (`values.yaml:434-450`) and no
  key moves;
- a new `broker.enabled` switch gates the broker itself;
- resource names are unchanged, so Plane's default broker (`plane.yaml:3-8`),
  `VIBEY_BUS_URL` (`worker.yaml:236-248`) and cluster-smoke keep working.

The worker also needs the AMQP URL and the backend and invocation switches. The
defaults stay `postgres` and `subprocess` until R34.

## Required behaviour
1. **values.yaml** gains these blocks:
   ```yaml
   broker:
     enabled: true
     existingSecret: ""
     existingSecretUrlKey: amqp-url
     existingSecretKedaHostKey: keda-host
     vhost: "/"
     prefix: vibey
   queue:
     backend: postgres
     rabbitmq:
       deliveryLimit: 20
       consumerTimeoutSeconds: 21600
       waitTiersSeconds: [1, 5, 30, 120, 600, 3600]
       reconcileIntervalSeconds: 30
       redispatchAfterSeconds: 900
   engines:
     invocation: subprocess
   ```
   Each key has a comment saying what it does, like its neighbours.
2. **`templates/broker.yaml`** renders the Secret, PVC, Service and Deployment now at
   `surfaces.yaml:101-199`. It is gated by `broker.enabled`, not by `surfaces.*`. It
   reads `surfaces.rabbitmq.*` for image, credentials, storage and resources, and keeps
   the same names and labels.
   - The Secret gains `amqp-url`:
     `amqp://<user>:<pass>@<fullName>-rabbitmq.<ns>.svc.<clusterDomain>:5672/<urlquery vhost>`.
   - It also gains `keda-host`:
     `http://<user>:<pass>@<fullName>-rabbitmq.<ns>.svc.<clusterDomain>:15672/`.
     Both use the qualified DNS, which is ADR-0025's lesson.
   - A ConfigMap `<fullName>-rabbitmq-conf` holds `20-vibey.conf` with
     `consumer_timeout = <consumerTimeoutSeconds * 1000>`. It is mounted at
     `/etc/rabbitmq/conf.d/20-vibey.conf`. This is the fallback ADR-0044 names for a
     broker that refuses the per-queue argument.
3. **`surfaces.yaml`** keeps only the bus `VibeySurface` CR from section 2, gated as
   today by `surfaces.enabled` and `surfaces.rabbitmq.enabled`.
4. **`plane.yaml:5-6`**: the fail condition becomes `not .Values.broker.enabled`, with
   the message naming `broker.enabled`.
5. **The worker** (`worker.yaml`) gains:
   - `VIBEY_QUEUE_BACKEND={{ .Values.queue.backend }}`
   - `VIBEY_ENGINE_INVOCATION={{ .Values.engines.invocation }}`
   - `VIBEY_BUS_VHOST` and `VIBEY_BUS_PREFIX`
   - `VIBEY_BUS_AMQP_URL` from `secretKeyRef`: the broker Secret's `amqp-url` when
     `broker.enabled`, else `broker.existingSecret` / `existingSecretUrlKey`, with
     `optional: true` only when neither is set
   - when `queue.backend=rabbitmq` or `engines.invocation=service`, an init container
     `wait-for-rabbitmq` that uses the vibey image, running
     `python -c` with a TCP-connect retry loop to `<fullName>-rabbitmq:5672` or the
     external host. It follows the `wait-for-postgres` pattern at `worker.yaml:40-58`.
6. **Goldens.** Regenerate with `deploy/helm/golden/render.sh --update`, then review.
   `default`, `ollama`, `ollama-gpu-qwenloop` and `surfaces-off` change. `keda-latest`
   and `keda-project` **must not change**. `surfaces-off` now contains the broker.

## Where to change
- The files on the card. Copy `templates/postgres.yaml`'s core-infrastructure shape.

## Acceptance criteria
- [ ] `render.sh` passes after `--update`, and `git diff deploy/helm/golden/keda-*.yaml` is empty.
- [ ] The `surfaces-off` golden contains `kind: Deployment` named `vibey-vibey-rabbitmq`.
- [ ] The worker env holds `VIBEY_BUS_AMQP_URL` from the broker Secret.
- [ ] `helm lint --strict` passes with `--set broker.enabled=false --set broker.existingSecret=x --set surfaces.plane.enabled=false`.
- [ ] `test_keda_scaler_query.py` passes unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_broker_golden.py`, module-level functions reading
  the goldens with `yaml.safe_load_all`, as `test_keda_scaler_query.py:34-39` does:
  - `test_broker_renders_with_surfaces_off`
  - `test_broker_secret_carries_qualified_urls`
  - `test_worker_reads_the_amqp_url_from_the_broker_secret`
  - `test_consumer_timeout_conf_is_mounted`
  - `test_bus_surface_cr_still_follows_surfaces`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_broker_golden.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- Loop-service Deployments (R30).
- KEDA (R31).
- CI (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R30 — chart-loop-services

**Lane card.**

- **Depends on:** R27, R29.
- **Wave:** 8.
- **Files touched:**
  - `deploy/helm/vibey/templates/loop-services.yaml` (new)
  - `deploy/helm/vibey/templates/worker.yaml` (worktrees access mode, affinity label, root env)
  - `deploy/helm/vibey/values.yaml`
  - the goldens (regenerated)
  - `tests/infrastructure/test_chart_loop_services_golden.py` (new)
- **Parallel-safe with:** R28 and R33.
- **Must keep passing unchanged:**
  - the `keda-*` goldens
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - R29's tests
  - all protected tests
- **Standing constraints:** see the header list. helm v4.2.4; never hand-edit goldens.

## Title
feat(chart): one Deployment per loop service

## Why
ADR-0044 §13 and §15 run each loop engine as one long-lived service. In a cluster that
means one Deployment per engine running `vibey loop-service --engine <id>` (R27).

Sub-doctrine 8.b makes qwenloop and opencode on by default and the paid engines
declared-only. A service edits the worktree its caller tails, so it must mount the
worker's worktrees PVC (`worker.yaml:276-310`) at the same path.

That PVC is `ReadWriteOnce` today. So either every pod that mounts it co-locates on
one node, or the operator chooses `ReadWriteMany`, which becomes a value (12.c). The
qwenloop service takes the Ollama wiring the worker has today (`worker.yaml:93-114`).

## Required behaviour
1. **values.yaml:**
   - `worker.worktrees.accessMode: ReadWriteOnce`
   - `loopServices:`, a map keyed by engine id: `qwenloop`, `opencode`, `claudeloop`,
     `codexloop`, `cursorloop`, `agyloop`, `claudeloop-local`. Each entry has:
     - `enabled` (true only for `qwenloop` and `opencode`)
     - `prefetch: 1`
     - `replicas: 1`
     - `terminationGracePeriodSeconds: 7200`
     - `engineAuth` (true for the four paid engines, false otherwise)
     - `resources`, with the worker's shape
     - `extraEnv: []`
2. **`templates/loop-services.yaml`:** for each enabled entry, a Deployment
   `<fullName>-loop-<engine>`:
   - labels: `app.kubernetes.io/component: loop-<engine>` and
     `vibey.dev/worktrees: <Release.Name>`;
   - `args: ["loop-service", "--engine", <engine>, "--prefetch", <prefetch>]`;
   - env:
     - `VIBEY_BUS_AMQP_URL`, `VIBEY_BUS_VHOST` and `VIBEY_BUS_PREFIX`, the same as
       R29's worker env;
     - `VIBEY_LOOP_SERVICES_ROOT=/work`;
     - for `qwenloop` with `ollama.enabled`, the same `VIBEY_OLLAMA_URL`,
       `VIBEY_OLLAMA_MODEL`, `QWENLOOP_BASE_URL` and `QWENLOOP_MODEL` lines as
       `worker.yaml:93-114`;
     - with `engineAuth`, the `engineAuth.keys` list as `worker.yaml:84-90` renders it;
     - then `extraEnv`;
   - the worktrees volume mounted at `/work`, `workingDir: /work`;
   - `podSecurityContext` and `securityContext`, and the chart's
     `nodeSelector` / `tolerations`.
3. **Affinity.** When `worker.worktrees.accessMode` is `ReadWriteOnce`, the worker and
   every loop service carry `vibey.dev/worktrees: <Release.Name>` and a **required**
   `podAffinity` on that label with `topologyKey: kubernetes.io/hostname`. The first
   pod may schedule because it matches its own term. `ReadWriteMany` renders no
   affinity.
4. **The PVC.** `accessModes: [{{ .Values.worker.worktrees.accessMode }}]`.
5. **Environment.** The worker also gets `VIBEY_LOOP_SERVICES_ROOT=/work`. R01 reads
   it as `[loop_services] root`.
6. **Goldens.** Regenerate `default`, `ollama`, `ollama-gpu-qwenloop` and
   `surfaces-off`. The `keda-*` goldens do not change.

## Where to change
- The files on the card. Copy the worker Deployment's shape.

## Acceptance criteria
- [ ] The default render has exactly two loop-service Deployments, qwenloop and opencode.
- [ ] Paid ones appear only when their `enabled` is set.
- [ ] The affinity is present under RWO and absent under RWX.
- [ ] The qwenloop service carries the Ollama env when `ollama.enabled`.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.

## Tests to write first (TDD)
- `tests/infrastructure/test_chart_loop_services_golden.py`:
  - `test_default_render_runs_the_sovereign_pair`
  - `test_services_mount_worktrees_at_work`
  - `test_rwo_renders_required_co_location`
  - `test_qwenloop_service_gets_the_ollama_wiring` (reads the `ollama` golden)
  - `test_paid_services_are_declared_only`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_chart_loop_services_golden.py tests/infrastructure/test_chart_broker_golden.py tests/infrastructure/db/test_keda_scaler_query.py tests/infrastructure/test_config_loader.py

## Out of scope
- KEDA (R31).
- CI (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R31 — chart-keda-rabbitmq

**Lane card.**

- **Depends on:** R29, R30.
- **Wave:** 9.
- **Files touched:**
  - `deploy/helm/vibey/templates/keda-scaledobject.yaml`
  - `deploy/helm/vibey/templates/_helpers.tpl` (at most one helper)
  - `deploy/helm/golden/render.sh`
  - `deploy/helm/golden/keda-rabbitmq.yaml` (new golden)
  - `tests/infrastructure/queue/test_keda_rabbitmq_trigger.py` (new)
- **Parallel-safe with:** R33.
- **Must keep passing unchanged:**
  - `tests/infrastructure/db/test_keda_scaler_query.py`
  - the `keda-latest` and `keda-project` goldens, byte for byte
  - all protected tests
- **Standing constraints:** see the header list. helm v4.2.4; never hand-edit goldens.

## Title
feat(chart): KEDA scales on the project's RabbitMQ queue

## Why
ADR-0044 §12. KEDA today scales on a PostgreSQL copy of the claim's SELECT arm
(`templates/keda-scaledobject.yaml:49-66`), bound to the real claim by
`tests/infrastructure/db/test_keda_scaler_query.py`.

In the RabbitMQ backend the queue holds only due work whose dependencies are met, so
its length (ready plus unacknowledged) is claimable work plus in-flight work. That
honours ADR-0025's rule against scaling on raw depth, and a pod mid-session is not
scaled in under its running job.

A broker cannot know which project is "newest", so the unbound worker mode cannot be
followed. The chart must fail loudly and name the fixes, rather than scale on
something no worker will claim.

## Required behaviour
1. `keda-scaledobject.yaml`:
   - When `queue.backend` is `postgres`, it renders **exactly** today's text.
   - When it is `rabbitmq`:
     - With `worker.project` empty, fail with:
       `"keda.enabled with queue.backend=rabbitmq needs worker.project: a broker cannot follow 'the newest project'. Set worker.project, or set queue.backend=postgres."`
     - Otherwise render a `TriggerAuthentication` `<fullName>-worker-rabbitmq`, whose
       `secretTargetRef` has parameter `host`. It points at the broker Secret's
       `keda-host` key, or at `broker.existingSecret` / `existingSecretKedaHostKey`.
     - Render the trigger:
       ```yaml
       - type: rabbitmq
         metadata:
           protocol: http
           mode: QueueLength
           value: "<worker.parallelism>"
           activationValue: "0"
           queueName: "<broker.prefix>.jobs.<canonical lower-case project uuid>"
           vhostName: "<broker.vhost>"
           excludeUnacknowledged: "false"
         authenticationRef:
           name: <fullName>-worker-rabbitmq
       ```
2. `queueName` must equal `QueueNames(prefix).project_queue(UUID(worker.project))`
   (R06). Add a `vibey.workerProjectUuid` helper next to `vibey.workerProjectHex` if
   the existing helper does not already give the canonical dashed lower-case form.
3. `render.sh`:
   - `keda-latest` and `keda-project` add `--set queue.backend=postgres`, so their
     goldens are unchanged.
   - A new profile:
     `profile keda-rabbitmq --show-only templates/keda-scaledobject.yaml -- --set keda.enabled=true --set queue.backend=rabbitmq --set worker.project="$PROJECT"`.
   - A new `expect_fail NAME ARGS…` function asserts that `helm template` fails. It is
     used once, for `--set keda.enabled=true --set queue.backend=rabbitmq`.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] `render.sh` passes, and the `keda-latest` and `keda-project` goldens are byte-identical.
- [ ] The `keda-rabbitmq` golden holds the trigger and the TriggerAuthentication.
- [ ] The unbound rabbitmq render fails with the message.
- [ ] The new test binds `queueName` to `QueueNames`.

## Tests to write first (TDD)
- `tests/infrastructure/queue/test_keda_rabbitmq_trigger.py`, reading the
  `keda-rabbitmq` golden:
  - `test_queue_name_is_the_projects_queue`
  - `test_counts_in_flight_work`
  - `test_value_is_the_worker_parallelism`
  - `test_authentication_uses_the_qualified_keda_host`

## Checks the lane must run (all must pass)
    deploy/helm/golden/render.sh
    git diff --exit-code deploy/helm/golden/keda-latest.yaml deploy/helm/golden/keda-project.yaml
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/infrastructure/queue/test_keda_rabbitmq_trigger.py tests/infrastructure/db/test_keda_scaler_query.py

## Out of scope
- The cluster contract (R32).
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R32 — ci-rabbitmq

**Lane card.**

- **Depends on:** R18, R30, R31.
- **Wave:** 10.
- **Files touched:** `.github/workflows/ci.yml`.
- **Parallel-safe with:** nothing that edits `ci.yml`.
- **Must keep passing unchanged:**
  - `tests/meta/test_postgres_support_matrix.py`; the 14–18 matrix is untouched
  - `tests/meta/test_tools_matrix_covers_every_package.py`
  - every existing job name. `noloss` is a required check (`ci.yml:98-104`), so no job
    is renamed.
  - all protected tests
- **Standing constraints:** see the header list.

## Title
ci: a RabbitMQ service in the gates and three cluster contracts for the broker

## Why
ADR-0044 §16. The contract suite (R18), the topology and relay integration tests
(R12, R13), and the chaos twin need a real broker in CI, or the "verification owed"
list in the ADR is never discharged.

The cluster must also prove three things against the pinned broker image
(`values.yaml:434-440`):

- the core broker exists;
- each enabled loop service consumes its queue;
- the RabbitMQ `ScaledObject` becomes Ready.

## Required behaviour
1. **`gates` job** (`ci.yml:30-96`). Add a service `rabbitmq` using the same image
   *and digest* as `values.yaml:436-439`:
   - `RABBITMQ_DEFAULT_USER=vibey` and `RABBITMQ_DEFAULT_PASS=vibey` (the default
     `guest` account refuses non-loopback connections);
   - ports `5672:5672` and `15672:15672`;
   - health check `rabbitmq-diagnostics -q ping`, interval 10 s, 12 retries.

   Add `VIBEY_TEST_AMQP_URL: amqp://vibey:vibey@localhost:5672/` to the job env.
2. **`cluster-smoke`.** After "the worker picks up a project created in-cluster"
   (`:956-966`), add:
   - `Contract - every enabled loop service consumes its queue`:
     - `kubectl wait --for=condition=available deployment/vibey-vibey-loop-qwenloop deployment/vibey-vibey-loop-opencode -n vibey --timeout=5m`
     - then `kubectl exec -n vibey deploy/vibey-vibey-rabbitmq -- rabbitmqctl list_queues name consumers`
     - assert that `vibey.runs.qwenloop` and `vibey.runs.opencode` each show at least 1
       consumer, retrying for up to 2 minutes.
   - `Contract - the RabbitMQ ScaledObject reconciles`:
     - read the demo project's id from the worker log line or from `vibey status` (read
       `cli/main.py` for the exact output and parse it);
     - `helm upgrade vibey deploy/helm/vibey -n vibey --set keda.enabled=true --set queue.backend=rabbitmq --set worker.project=$ID --wait --timeout 5m`;
     - wait for the `ScaledObject` `Ready=True`, the same loop as `:980-988`.

   This step runs after the existing PostgreSQL `ScaledObject` contract and before the
   drain contract. The drain contract then upgrades with `--set keda.enabled=false`
   exactly as today.
3. `vibey-vibey-rabbitmq` stays in the availability list. Nothing else changes.

## Where to change
- `.github/workflows/ci.yml` only.

## Acceptance criteria
- [ ] `ci.yml` parses (`python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"`).
- [ ] The meta tests pass.
- [ ] Locally, with a broker at `VIBEY_TEST_AMQP_URL`, `uv run pytest -m integration tests/infrastructure/queue tests/contracts` passes.
- [ ] The cluster steps are syntax-checked (`bash -n` on each extracted `run` block).

## Tests to write first (TDD)
- No new test file. The contracts are the tests. Run `tests/meta` to prove the matrix
  bindings still hold.

## Checks the lane must run (all must pass)
    uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
    uv run pytest -q -p no:cacheprovider tests/meta
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- Flipping the defaults (R34), which updates the existing PostgreSQL `ScaledObject`
  step to pin `queue.backend=postgres`.
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R33 — install-and-doctor

**Lane card.**

- **Depends on:** R28.
- **Wave:** 9.
- **Files touched:**
  - `src/vibey/infrastructure/rabbitmq_local.py` (new)
  - `src/vibey/infrastructure/interfaces/rabbitmq_local_interface.py` (new)
  - `src/vibey/cli/main.py` (`install` at `:1156`; doctor's checks)
  - `tests/infrastructure/test_rabbitmq_local.py` (new)
  - `tests/cli/test_operational_commands.py` (new tests)
- **Parallel-safe with:** R30 and R31.
- **Must keep passing unchanged:**
  - `tests/infrastructure/test_postgres_local.py`
  - every existing `install` and `doctor` test in `tests/cli/*`
  - all protected tests
- **Standing constraints:** see the header list.

## Title
feat(cli): vibey install --rabbitmq, and doctor checks the broker and every loop service

## Why
ADR-0044's *Migration* section. Once R34 flips the defaults, a laptop with no broker
fails with `QueueBackendNotConfigured`. The fix must be one command, as
`vibey install --postgres` is for PostgreSQL (`cli/main.py:1156-1180`, backed by
`PostgresLocalService` at `infrastructure/postgres.py:134-390`).

`vibey doctor` must also say whether the broker answers and whether each engine's loop
service is consuming. Otherwise a worker whose runs sit in a queue nobody consumes
looks healthy.

## Required behaviour
1. `class RabbitMqLocalService` mirrors `PostgresLocalService`:
   - `status()` reports whether `rabbitmq-server` or `rabbitmqctl` is on `PATH`, and
     whether `rabbitmq-diagnostics -q ping` exits 0.
   - `install()` uses Homebrew (`brew install rabbitmq`, `brew services start rabbitmq`),
     apt (`rabbitmq-server` plus a service start) or dnf (`rabbitmq-server` plus a
     service start).
   - It uses the same `_privileged` and step-recording approach, and the same result
     dataclasses (new `RabbitMqStatus` and `RabbitMqInstallResult`).
2. `vibey install --rabbitmq`:
   - It is independent of `--postgres`, and both flags may be given.
   - On success it prints `export VIBEY_BUS_AMQP_URL=amqp://guest:guest@localhost:5672/`.
     The `guest` account works on loopback only, and the output says so.
   - With neither flag, the usage line names both flags.
3. `vibey doctor`, when the resolved backend is `rabbitmq` or the invocation is `service`:
   - It connects with `AmqpClient` and reports `broker: ok <redacted url>`, or
     `broker: unreachable (<error>)`. An unreachable broker makes the exit non-zero.
   - In `service` mode, for each engine in the pool, it probes `--version` through
     `LoopServiceClient.probe` with a 10 s timeout, and reports
     `loop-service <engine>: answering (<version>)` or
     `loop-service <engine>: no service answered; start one with vibey loop-service --engine <engine>`.
   - With the defaults (`postgres` and `subprocess`), doctor's output is unchanged.

## Where to change
- The new module, its interface, and `cli/main.py`.

## Acceptance criteria
- [ ] Each package-manager path is tested with a fake runner, as `test_postgres_local.py` does.
- [ ] `install --rabbitmq` prints the export line.
- [ ] Doctor reports an unreachable broker and exits non-zero.
- [ ] Doctor reports a silent loop service.
- [ ] Doctor's default output is unchanged.
- [ ] 100% coverage on `cli/` and `infrastructure/`.

## Tests to write first (TDD)
- `tests/infrastructure/test_rabbitmq_local.py`: mirror each `test_postgres_local.py`
  case for brew, apt, dnf, an unsupported platform, and a failed start.
- `tests/cli/test_operational_commands.py`:
  - `test_install_rabbitmq_prints_the_export_line`
  - `test_doctor_reports_an_unreachable_broker`
  - `test_doctor_reports_a_silent_loop_service`
  - `test_doctor_default_output_is_unchanged`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_rabbitmq_local.py tests/infrastructure/test_postgres_local.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Flipping the defaults (R34).
- Docs and CHANGELOG.

Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R34 — defaults-flip

**Lane card.**

- **Depends on:** R01–R33, all merged.
- **Wave:** 11.
- **Files touched:**
  - `src/vibey/domain/config.py` (two defaults)
  - `src/vibey/bootstrap.py` or `infrastructure/queue/selection.py` (the `QueueBackendNotConfigured` message)
  - `tests/domain/test_config.py` (R01's default test)
  - `tests/conftest.py`
  - `deploy/helm/vibey/values.yaml`
  - `deploy/helm/golden/*` (regenerated)
  - `.github/workflows/ci.yml` (one step pins `postgres`)
- **Parallel-safe with:** nothing.
- **Must keep passing unchanged:** the entire suite, including all protected tests, the
  `keda-*` goldens and `test_keda_scaler_query.py`.
- **Standing constraints:** see the header list.

## Title
feat(queue)!: RabbitMQ dispatch and loop services are the defaults

## Why
ADR-0044 §1 and §13. By the time this lane runs, the evidence the ADR owes before the
flip has landed and is green:

- the contract suite on both backends (R18);
- the chaos twin (R18);
- the supersede and dedupe tests (R22);
- the cluster contracts (R32);
- a one-command local broker (R33).

This lane changes only defaults, so reverting it restores today's behaviour
completely. That is CDD's bounded divergence (sub-doctrine 9.c).

## Required behaviour
1. `QueueConfig.backend` defaults to `"rabbitmq"`, and `EnginesConfig.invocation` to
   `"service"`. R01's `test_queue_defaults_to_postgres_and_subprocess` is renamed to
   `test_queue_defaults_to_rabbitmq_and_service` and asserts the new defaults. This is
   the only edit to an existing assertion.
2. `tests/conftest.py` `pytest_configure` (`:146-156`) adds, with a comment:
   ```python
   os.environ.setdefault("VIBEY_QUEUE_BACKEND", "postgres")
   os.environ.setdefault("VIBEY_ENGINE_INVOCATION", "subprocess")
   ```
   The comment says the historical suite was written for these, the contract suite
   (R18) proves both backends, and `setdefault` lets CI or a developer run the suite on
   another backend.
3. `QueueBackendNotConfigured`'s message adds a third remedy: `vibey install --rabbitmq`.
4. `values.yaml`: `queue.backend: rabbitmq` and `engines.invocation: service`.
5. `ci.yml`'s existing step "the ScaledObject reconciles against real Postgres"
   (`:973-991`) adds `--set queue.backend=postgres` to its `helm upgrade`, so that step
   keeps testing the PostgreSQL trigger.
6. Regenerate the goldens. `keda-latest` and `keda-project` stay byte-identical,
   because R31 pinned them.
7. The commit carries a `BREAKING CHANGE:` footer. Its text: vibey now needs a
   RabbitMQ broker by default (`VIBEY_BUS_AMQP_URL`); `vibey install --rabbitmq`
   installs one; `VIBEY_QUEUE_BACKEND=postgres` with
   `VIBEY_ENGINE_INVOCATION=subprocess` restores the one-daemon behaviour; and in the
   chart, `keda.enabled` now needs `worker.project` unless `queue.backend=postgres`.

## Where to change
- The files on the card.

## Acceptance criteria
- [ ] The whole suite passes with the conftest pin.
- [ ] `VIBEY_QUEUE_BACKEND=rabbitmq VIBEY_TEST_AMQP_URL=… uv run pytest tests/contracts tests/infrastructure/queue` passes against a local broker.
- [ ] `render.sh` passes, and the `keda-*` goldens are unchanged.
- [ ] `git diff --stat` shows no protected file.

## Tests to write first (TDD)
- Rename and update the default test (behaviour 1).
- `tests/test_bootstrap.py`: `test_defaults_without_a_broker_name_all_three_remedies`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100
    uv run coverage report --include='src/vibey/application/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    deploy/helm/golden/render.sh
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Docs, ADRs and CHANGELOG (R35).

Do not push. Commit locally as `feat(queue)!: …` with the `BREAKING CHANGE:` footer.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.

---

# Lane R35 — docs-wave (owned by the docs wave, not a 14B lane)

**Lane card.**

- **Depends on:** R34.
- **Wave:** 12.
- **Files touched:** documentation, ADRs and governance only.
- **Must keep passing unchanged:** the doc meta-tests:
  - `tests/meta/test_adr_counts.py` (counts and nav)
  - `tests/meta/test_paper_renders.py`
  - `tests/meta/test_paper_evidence.py`
  - `tests/meta/test_phase_diagram.py`

## Title
docs: ADR-0044, the queue port, RabbitMQ dispatch and loop services

## Why
CLAUDE.md, the ADRs, the data-model and architecture plans, and the paper all state
"PostgreSQL `SKIP LOCKED` is the queue" as a present fact. The docs wave owns those
surfaces (`SPEC-TEMPLATE.md`, *Out of scope*). An ADR that is not in the nav, with
counts that disagree, fails `tests/meta/test_adr_counts.py`.

## Required behaviour
1. Land `specs/ADR-rabbitmq-queue.md` as
   `docs/architecture/decisions/0044-the-job-queue-is-a-port.md`, keeping the status
   *proposed* until the operator merges it. Add it to the `properdocs.yml` nav, and
   update "(N ADRs" to 44 in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md` and
   `docs/index.md`.
2. Status notes:
   - ADR-0002: "superseded in part by ADR-0044 (dispatch); its record-store and ledger
     decisions stand".
   - ADR-0025: the autoscaling trigger is amended by ADR-0044 §12.
   - ADR-0009: an answer also re-dispatches (ADR-0044 §6).
3. `docs/plans/data-model.md`:
   - §1: the requirement table gains a RabbitMQ column.
   - §3.3: `dispatch_seq` and `dispatched_at`.
   - §3.4: add the lease-mapping table (ADR-0044 §5).
   - A new §3.11 for `job_outbox`.
   - §4: notifications in both backends.
   - The relation count in the status note.
4. `docs/plans/architecture-and-roadmap.md`:
   - §4 container view: the broker, the loop services, and replacing "Adapters →
     subprocess" with "→ loop service".
   - The process model.
   - §7.1–§7.4.
5. `docs/paper.md`:
   - *Queue semantics*: two backends. The strict-priority claim holds for PostgreSQL;
     the RabbitMQ ordering is FIFO with best-effort priority.
   - *Validation*: the chaos twin.
   - Keep `test_paper_evidence.py` green.
6. CLAUDE.md, AGENTS.md and GEMINI.md: the "Queue backend" fact, the engines and
   invocation fact, and the commands block. Update the four agent-surface trees
   (`.claude/skills/`, `.cursor/rules/`, `.agents/skills/`, `.agent/rules/`) in the
   same PR: architecture, engine-adapters, testing, quality-gates.
7. `docs/reference/cli.md`: `loop-service`, `loop submit`, `install --rabbitmq`.
8. `docs/reference/configuration.md`: `[queue]`, `[bus]` AMQP keys, `[engines] invocation`,
   `[loop_services]`.
9. `docs/guides/kubernetes.md`: the core broker, the loop services, worktree access
   modes, and the KEDA requirement.
10. `CHANGELOG.md`, through the release tooling's usual path.
11. **Owed to the operator, not writable by this lane:** an amendment to sub-doctrine
    8.b (`src/vibey_tools/gh/docs/doctrines.md:109-142`, plus `corpus-index.json`) that
    names the Bus surface and its RabbitMQ default. ADR-0044 flags that the operator's
    decision cites a ratification the canon does not record.

## Where to change
- The files listed above.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.
- [ ] The book and paper build as in the docs job.

## Tests to write first (TDD)
- None. The doc meta-tests are the tests.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Code.
- The canon amendment (the operator's).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
