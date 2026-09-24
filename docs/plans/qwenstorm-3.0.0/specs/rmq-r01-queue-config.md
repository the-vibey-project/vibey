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

## Lane card
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
