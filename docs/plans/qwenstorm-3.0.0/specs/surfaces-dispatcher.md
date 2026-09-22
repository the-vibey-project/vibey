## Title
feat(surfaces): SurfaceRequestDispatcher handles one delivery — decode, dedupe, execute, persist, reply or dead-letter, record, then settle

## Why
Draft ADR-0047 §6–§9 (`specs/ADR-surface-lanes.md`) fix what a lane does with each delivery:

- a malformed message, or one for the wrong surface, is dead-lettered by the lane
  ("`dead_letter()`; the broker adds `x-death`", §9 table);
- "a redelivery of one that is still running (a channel blip) starts nothing (as R22 rule b)" (§8);
- "Where a caller is waiting (answer or ack), a failure is **replied**, not dead-lettered …
  Only outcomes that nobody would otherwise see become dead letters" (§9): the lane "publishes
  a `vibey.surface.dead/1` evidence message to the DLX (confirmed), **then** completes the
  original delivery";
- ADR-0044's settle order: "persist the result, then publish, then acknowledge" (§4 of this
  record's conventions table).

Two decisions this lane makes where the ADR is silent: an operation that parks with an unknown
outcome is **always** dead-lettered, even when a caller is waiting, because a person must find
it in `vibey surface dead-letters` to grant it; and the ledger and measurement are written
**before** the acknowledgement, so a lane that dies in between repeats the record, never loses
it (7.c). ADR-0047 lane S23 (the per-delivery half of the host).

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/dispatcher.py`, `class SurfaceRequestDispatcher`:

1. `__init__(self, *, surface: SurfaceName, client: AmqpClientInterface, names: SurfaceQueueNamesInterface, executor: SurfaceExecutorInterface, guarded: SurfaceExecutorInterface | None, recorder: SurfaceLedgerRecorderInterface, meter: SurfaceLaneMeterInterface, clock: Clock, logger: Logger, instance: str, backend: str, started_at: datetime, codec: SurfaceProtocolCodecInterface = SURFACE_PROTOCOL, redactor: SurfaceRequestRedactorInterface = SURFACE_REDACTOR, catalogue: SurfaceCatalogueInterface = CATALOGUE)`.
   `executor` runs every non-guarded operation (for the cache surface it is the
   `CacheLaneHandler`); `guarded` runs `GUARDED` operations and must be given when the surface
   has one (`ValueError` at construction otherwise).
2. `async handle(self, delivery: AmqpDeliveryInterface) -> None`:
   1. `codec.request_from_bytes(delivery.body)`; on `MalformedSurfaceMessage`:
      `meter.observe_malformed()`, log `surface.request_malformed` at `warning` with the body
      length only, `await delivery.dead_letter()`, return.
   2. A request for another surface: `observe_malformed()`, log `surface.request_wrong_surface`,
      `await delivery.dead_letter()`, return.
   3. When `request.request_id` is already executing, append the delivery to that entry, log
      `surface.redelivery_while_active` at `info`, and return; it is settled with the first.
   4. Otherwise register it, and in `try … finally` (always unregister):
      1. **Execute.** `_ping` → `OK` with result
         `{"surface", "instance", "backend", "started_at" (ISO), "pid"}`. Otherwise the guarded
         executor for a `GUARDED` spec, else `executor`. An unexpected exception becomes `ERROR`,
         `dead_reason=FAILED`, logged `surface.executor_failed` at `error`.
      2. **Reply** when `delivery.properties.reply_to` is set: publish
         `codec.reply_to_bytes(SurfaceReply(request_id, op_id, outcome.status, outcome.result, codec.clip(outcome.detail), outcome.replayed, instance, outcome.finished_at or clock.now()))`
         to exchange `""` with routing key `reply_to`,
         `AmqpProperties(correlation_id=request_id, type="surface.reply", delivery_mode=1)`,
         `mandatory=False, confirm=False`. A publish error is logged `surface.reply_failed`
         (the caller times out) and does not stop the rest.
      3. **Dead-letter** when `outcome.dead_reason` is set and (no `reply_to`, or the reason is
         `OUTCOME_UNKNOWN`): build `SurfaceDeadLetter` with the reason, the clipped detail,
         `outcome.attempts`, `delivery.delivery_count`, `instance`, `clock.now()`, and
         `request = codec.encode_request(request)` with its `"args"` replaced by
         `redactor.for_dead_letter(spec, request.args).args`, and `retained` from the same
         call; publish `codec.dead_to_bytes(dead)` to `names.dead_exchange()` with
         `names.write_key(surface)`, `AmqpProperties(message_id=dead.message_id, type="surface.dead", delivery_mode=2)`,
         `mandatory=True, confirm=True`. If that publish fails, log `surface.dead_letter_failed`
         at `error`, `await d.abandon()` for every delivery of this request, and return (the
         redelivery is safe: guarded operations answer from their record, native ones are
         deduplicated by the backend).
      4. **Record** `await recorder.record_outcome(request, outcome, instance=instance)` and
         `meter.observe(request, outcome)`.
      5. **Settle** `await d.complete()` for every delivery of this request.
3. `active(self) -> int`: how many requests are executing (the host's drain reads it).
4. **Interface** `surface_lanes/interfaces/dispatcher_interface.py`:
   `@runtime_checkable class SurfaceRequestDispatcherInterface(Protocol)` with `handle` and
   `active`; exported. Registry: the real class over `InMemoryAmqpClient`, a handler over
   `InMemoryTracker`, the in-memory recorder and meter (a `functools.partial` building fresh
   parts), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/dispatcher.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/dispatcher_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_dispatcher.py`.

## Acceptance criteria
- [ ] With the topology declared on `memory_amqp`: a malformed body and a wrong-surface request each end in `vibey.surface.<s>.dead` through `dead_letter()`, and the meter counts them.
- [ ] An answer-mode request is replied on its `reply_to` with the matching `correlation_id`, then completed; the reply is published to the default exchange, unconfirmed.
- [ ] A send with no `reply_to` that fails permanently publishes one `surface.dead` message with `message_id == "<request_id>:failed"` and redacted args, then completes; a successful send publishes nothing extra.
- [ ] A guarded send that parks while a caller waits is both replied `parked` and dead-lettered `outcome_unknown`.
- [ ] If the evidence publish is refused (no dead exchange declared), the delivery is abandoned, not completed.
- [ ] A redelivery of an executing request starts nothing; both deliveries are completed when the first finishes, and one reply is sent.
- [ ] `_ping` is answered with the instance, backend and start time.
- [ ] A request bound to a project leaves one `SurfaceOperationRecorded` event in `InMemoryLedger`, written before the delivery is completed.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_dispatcher.py` (no service; `memory_amqp` with `SurfaceLaneTopology.declare`, deliveries taken with `memory_amqp.get(...)` after publishing through the real `SurfaceLaneClient` or raw bytes, in-memory adapters, `InMemorySurfaceOperationRepository`, `InMemoryLedger`, `InMemoryProjectRepository`, `RecordingLogger`, `FakeClock`, and a blocking executor class in the module for the redelivery case):
- `test_a_malformed_message_is_dead_lettered_by_the_broker`
- `test_a_request_for_another_surface_is_dead_lettered`
- `test_an_answer_is_replied_then_completed`
- `test_a_failed_send_without_a_waiter_publishes_evidence_then_completes`
- `test_a_parked_send_is_replied_and_dead_lettered`
- `test_a_refused_evidence_publish_abandons_the_delivery`
- `test_a_redelivery_while_active_starts_nothing`
- `test_ping_is_answered_by_the_lane`
- `test_an_unexpected_executor_error_is_replied_as_error`
- `test_the_ledger_is_written_before_the_ack`
- `test_guarded_surfaces_need_a_guarded_executor`
- `test_dispatcher_satisfies_its_interface`

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
- Consuming, the lease, the reconcile tick and the drain (`surfaces-lane-host`); draining the dead
  queue into PostgreSQL (`surfaces-reconcile`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-guarded-execution`, `surfaces-cache-handler`, `surfaces-ledger-recorder`, `surfaces-lane-meter`, `surfaces-lane-client` (tests publish through it), `surfaces-topology`.
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
