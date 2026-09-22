## Title
feat(surfaces): SurfaceReplyRouter owns one reply queue per process and hands each reply to the call waiting for it

## Why
Draft ADR-0047 §6 (`specs/ADR-surface-lanes.md`), step 1: "On first use the client declares
one reply queue (server-named, exclusive, auto-delete) and consumes it. Each reply is routed to
its waiting call by `correlation_id`. A reply nobody is waiting for is acknowledged and
dropped." Replies travel transient on that exclusive queue, "that only its caller's connection
can consume" ("Security impact"). Separating the router from the client keeps each class to one
job and one test file; the client (`surfaces-lane-client`) only asks for a future. Part of
ADR-0047 lane S16. RabbitMQ's direct reply-to is deliberately not used yet (§10: held back until
the measurement exists).

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/reply_router.py`, `class SurfaceReplyRouter`:

1. `__init__(self, client: AmqpClientInterface, *, logger: Logger, codec: SurfaceProtocolCodecInterface = SURFACE_PROTOCOL, prefetch: int = 256)`.
2. `async reply_to(self) -> str`: on the first call (guarded by an `asyncio.Lock` so concurrent
   first calls declare once) it declares
   `await client.declare_queue("", exclusive=True, auto_delete=True, durable=False)`, keeps the
   returned name, and starts `client.consume(name, prefetch=self._prefetch, handler=self._on_reply)`.
   Every later call returns the same name.
3. `expect(self, request_id: str) -> asyncio.Future[SurfaceReply]`: registers and returns a
   future for that id. Registering an id twice raises `ValueError` (a caller bug).
4. `forget(self, request_id: str) -> None`: drops the waiting future, if any (after a timeout).
5. `async _on_reply(self, delivery: AmqpDeliveryInterface) -> None`:
   - decode with `codec.reply_from_bytes(delivery.body)`; on `MalformedSurfaceMessage` log
     `surface.reply_malformed` at `warning` (with the first 200 bytes' length only, never the
     body) and complete the delivery;
   - look up `delivery.properties.correlation_id`; when a future is waiting and not done, set
     its result to the reply and forget the id; otherwise log `surface.reply_unexpected` at
     `debug` with the correlation id;
   - always `await delivery.complete()`.
6. `async close(self) -> None`: cancels the consumer when one was started, and cancels every
   waiting future. Idempotent.
7. `src/vibey/infrastructure/surface_lanes/interfaces/reply_router_interface.py`:
   `@runtime_checkable class SurfaceReplyRouterInterface(Protocol)` with `reply_to`, `expect`,
   `forget`, `close`; exported from the interfaces `__init__.py`.
8. **Registry.** Register `SurfaceReplyRouterInterface → functools.partial(SurfaceReplyRouter, InMemoryAmqpClient(), logger=RecordingLogger())`
   and add it to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/reply_router.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/reply_router_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_reply_router.py`.

## Acceptance criteria
- [ ] Two concurrent first calls to `reply_to()` declare one server-named, exclusive, auto-delete, non-durable queue and one consumer.
- [ ] A reply published to the default exchange with that queue name and a matching `correlation_id` resolves the matching future only; the delivery is completed.
- [ ] A reply with an unknown or forgotten correlation id is completed and dropped; a malformed body is completed and logged without its content.
- [ ] `close()` cancels the consumer and every waiting future.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_reply_router.py` (no service; `memory_amqp`, `RecordingLogger`; replies published with `exchange=""`, lane `surfaces-amqp-publish-modes`):
- `test_reply_queue_is_declared_once_even_when_raced`
- `test_a_reply_resolves_its_own_future`
- `test_an_unexpected_reply_is_dropped_and_completed`
- `test_a_malformed_reply_is_completed_and_logged_without_its_body`
- `test_expecting_an_id_twice_is_refused`
- `test_close_cancels_the_consumer_and_the_waiters`
- `test_router_satisfies_its_interface`

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

## Out of scope
- Publishing requests and waiting with a deadline (`surfaces-lane-client`). CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not
  push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-caller-scope` (package, fixtures), `surfaces-protocol`, `surfaces-amqp-publish-modes` (publishing to `""` in the tests), `fakes-observability` (`RecordingLogger`).
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
