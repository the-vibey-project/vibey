## Title
feat(surfaces): SurfaceLaneTopology declares each lane's exchanges, write, read and dead queues with their exact arguments

## Why
Draft ADR-0047 §4 (`specs/ADR-surface-lanes.md`) fixes each surface's broker objects and their
arguments. Writes go to a **quorum** queue (single active consumer, delivery limit, at-least-once
dead-lettering, `reject-publish` with a length cap, a consumer timeout); reads go to a
**classic** queue of transient messages, "because a quorum queue commits every message to its
Raft log before it delivers it … a write to disk on the read path" (§4 "Why reads get their
own queue", §10). "The client and the lane both declare the topology … Declaring twice is
harmless, and a request published before its lane ever started still routes, and waits."
Sub-doctrine 12.c: the topology is declared by code, from keys, never clicked. ADR-0047 lane
S15. It also carries the broker facts the ADR owes ("Verification owed", items 3–6) as
integration tests against the pinned `rabbitmq:4-management-alpine`.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/topology.py`, `class SurfaceLaneTopology`:

1. `__init__(self, client: AmqpClientInterface, names: SurfaceQueueNamesInterface, settings: SurfacesConfigInterface)`.
2. `write_arguments(self, surface: SurfaceName) -> dict[str, object]` returns exactly:
   ```python
   {"x-queue-type": "quorum", "x-single-active-consumer": True,
    "x-delivery-limit": settings.delivery_limit,
    "x-dead-letter-exchange": names.dead_exchange(),
    "x-dead-letter-strategy": "at-least-once", "x-overflow": "reject-publish",
    "x-max-length": settings.write_max_length,
    "x-consumer-timeout": settings.consumer_timeout_seconds * 1000}
   ```
3. `read_arguments(self, surface) -> dict[str, object]` returns exactly:
   ```python
   {"x-queue-type": "classic", "x-single-active-consumer": True,
    "x-dead-letter-exchange": names.dead_exchange(),
    "x-overflow": "reject-publish", "x-max-length": settings.read_max_length}
   ```
4. `dead_arguments(self) -> dict[str, object]` returns `{"x-queue-type": "quorum"}`.
5. `async declare(self, surface: SurfaceName) -> None`, once per surface per instance (a set of
   declared surfaces; a second call returns at once):
   - `declare_exchange(names.request_exchange(), "topic")`, `declare_exchange(names.dead_exchange(), "direct")`;
   - `declare_queue(names.write_queue(s), arguments=write_arguments(s))` and
     `bind(write_queue, request_exchange, names.write_key(s))`;
   - `declare_queue(names.read_queue(s), arguments=read_arguments(s))` and
     `bind(read_queue, request_exchange, names.read_key(s))`;
   - `declare_queue(names.dead_queue(s), arguments=dead_arguments())`, bound to the dead
     exchange with **both** `write_key(s)` and `read_key(s)` (a dead-lettered message keeps its
     routing key, ADR §4 table).
   An `AmqpError` propagates unchanged; the surface is not marked declared.
6. `src/vibey/infrastructure/surface_lanes/interfaces/topology_interface.py`:
   `@runtime_checkable class SurfaceLaneTopologyInterface(Protocol)` with the four methods;
   exported from `surface_lanes/interfaces/__init__.py`.
7. **Registry.** Register `SurfaceLaneTopologyInterface → functools.partial(SurfaceLaneTopology, InMemoryAmqpClient(), SurfaceQueueNames(), SurfacesConfig())`
   (the real class over an in-memory broker, amendment A2) and add it to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/topology.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/topology_interface.py`; the interfaces
  `__init__.py` (export); `tests/fakes/registry.py` (append).
- New `tests/infrastructure/surface_lanes/test_topology.py` and
  `tests/infrastructure/surface_lanes/test_topology_integration.py`.

## Acceptance criteria
- [ ] Against `memory_amqp`, one `declare(SurfaceName.CACHE)` creates exactly two exchanges, three queues with the exact argument dicts, and four bindings; a second call declares nothing more.
- [ ] A message published to the request exchange with key `cache` lands in `vibey.surface.cache`, with key `cache.read` in `vibey.surface.cache.read`; a message dead-lettered from either lands in `vibey.surface.cache.dead`.
- [ ] A failing declare propagates and a later call retries it.
- [ ] Integration (`amqp_url`): the real broker accepts every argument of both queues (quorum with SAC, consumer timeout, max-length and reject-publish; classic with SAC); declaring twice succeeds; a confirmed publish into a full `reject-publish` queue (declared with `x-max-length: 1` under a unique name) raises `AmqpPublishError`; a 10 MiB body publishes to a scratch queue (RabbitMQ 4's default message-size limit is larger). These are the ADR's *Verification owed* items 3, 4 and 6; item 5 (a transient read does not survive a broker restart) cannot run inside a test and is recorded by `surfaces-cluster-smoke` as manual evidence.
- [ ] 100% `infrastructure/` branch coverage; the parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_topology.py` (no service; `memory_amqp`):
- `test_write_arguments_are_exact`
- `test_read_arguments_are_exact`
- `test_declare_creates_every_object_once`
- `test_routing_keys_reach_their_queues_and_the_dead_queue`
- `test_a_failed_declare_is_retried_next_time`
- `test_topology_satisfies_its_interface`
`tests/infrastructure/surface_lanes/test_topology_integration.py` (`amqp_url`, so integration):
- `test_the_broker_accepts_every_argument`
- `test_a_full_reject_publish_queue_nacks_a_confirmed_publish`
- `test_a_ten_mebibyte_message_is_accepted`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    # With a broker (record in the commit body whether it ran):
    VIBEY_TEST_AMQP_URL="$VIBEY_TEST_AMQP_URL" uv run pytest -q -p no:cacheprovider -m integration tests/infrastructure/surface_lanes/test_topology_integration.py

## Out of scope
- The lock queue (the lease declares it, `surfaces-lane-host`); publishing and consuming
  (`surfaces-lane-client`, `surfaces-lane-host`). CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or
  change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-caller-scope` (the package and test fixtures), `surfaces-queue-names`, `surfaces-config`, `surfaces-amqp-queue-limits` (the in-memory broker honours the arguments).
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam (the client is injected); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service; real-broker tests are integration and skip without `VIBEY_TEST_AMQP_URL`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
