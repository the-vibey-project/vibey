## Title
feat(test-harness): the harness service consumes one machine's queue, one run at a time

## Why
Sub-doctrine 8.e (ratified, `src/vibey_tools/gh/docs/doctrines.md:271-286`): "a single instance per
deployment … takes its work from a queue on the bus surface", and a run that dies is "moved to a
dead-letter queue with its evidence … never silently dropped". Draft ADR-0045 §9 and §12 set out
how the service handles each request:
1. it consumes the machine's queue with prefetch 1;
2. it hands each request to the same `HarnessInstance` the `local` backend uses (harness-T13), so a
   run means the same thing on both backends;
3. it lets the instance write the answer, **then** publishes it to the requester's reply queue,
   **then** settles the delivery — ADR-0044 §13's order;
4. a dead-letter outcome settles with `dead_letter()`, which moves the request, literally, to a
   dead-letter queue.

A reconcile tick drains that queue into the store: a request that died before anything was recorded
still becomes a visible dead letter. On SIGTERM a run cut short is abandoned and requeued, never
answered as a result. The settle vocabulary (`complete`, `abandon`, `dead_letter`) is rmq-r04's (10.e).

## Required behaviour
Create `src/vibey/infrastructure/test_harness/amqp_service.py`:
1. **`TestHarnessService`**, built with keyword-only arguments: `client: AmqpClientInterface`,
   `names: TestHarnessNamesInterface`, `topology: TestHarnessTopologyInterface`,
   `instance: HarnessInstanceInterface`, `codec: TestHarnessCodecInterface`,
   `store: TestRunStoreInterface`, `clock: Clock`, `settings: TestHarnessSettingsInterface`,
   `logger: Logger` (`vibey.application.interfaces.observability`, `:23-30`).
2. **`async def start(self) -> None`**: `await topology.declare()`;
   `self._tag = await client.consume(names.request_queue(), prefetch=1, handler=self._on_delivery)`;
   start a background task that calls `reconcile()` every `settings.reconcile_interval_seconds`.
3. **`_on_delivery(self, delivery: AmqpDeliveryInterface) -> None`** (async):
   1. decode with `codec.from_bytes(delivery.body)`. A `MalformedTestHarnessMessage`, or a message
      that is not a `TestRunRequest`, is logged (`logger.warning("test_harness_malformed_request", message_id=delivery.properties.message_id)`)
      and settled with `await delivery.dead_letter()`;
   2. otherwise `result = await instance.handle(request, delivery_count=delivery.delivery_count)`;
   3. if `delivery.properties.reply_to` is set, publish to exchange `""` with routing key
      `reply_to`, body `codec.to_bytes(result)`,
      `AmqpProperties(correlation_id=str(request.request_id), type="test.result")` and
      `mandatory=False`. A publish error (the requester is gone) is logged, never raised;
   4. settle: outcome `ABANDONED` → `await delivery.abandon()` (requeued, it runs again after the
      restart); status `EXECUTED` with `outcome.is_dead_letter()` → `await delivery.dead_letter()`;
      otherwise `await delivery.complete()`.

   While a delivery is being handled, the service remembers it as in flight.
4. **`async def reconcile(self) -> int`**: loop over `await client.get(names.dead_queue())` until it
   returns `None`:
   - undecodable → `store.put_malformed(delivery.body, message_id=delivery.properties.message_id, reason="undecodable request in the dead queue", received_at=clock.now())`, then `complete()`;
   - `store.dead_letter_for_request(request.request_id)` exists → `complete()`;
   - otherwise: `store.dead_letter(DeadLetter.from_request(request, run_id=uuid4(), outcome=CRASHED, reason=f"the request exceeded the delivery limit ({delivery.delivery_count} deliveries) before the service recorded it", record=None, at=clock.now()))`;
     `store.put_answer(<an EXECUTED result with outcome CRASHED, that run_id, key "unkeyed" and the reason as detail>)`;
     reply as in 3.3; `complete()`.

   It returns the number of messages handled.
5. **`async def stop(self, *, grace_seconds: float) -> None`**: `await client.cancel(self._tag)` and
   cancel the reconcile task; if a delivery is in flight, wait up to `grace_seconds` for it; then
   `await instance.abandon_current()` and wait for the handler to settle.
6. **The interface** `src/vibey/infrastructure/test_harness/interfaces/amqp_service_interface.py`:
   `@runtime_checkable` `TestHarnessServiceInterface` (`start`, `reconcile`, `stop`).

## Where to change
- New `src/vibey/infrastructure/test_harness/amqp_service.py` and its interface module.
- New `tests/infrastructure/test_harness/test_amqp_service.py`.

## Acceptance criteria
All with the registered fakes: `InMemoryAmqpClient` (the `memory_amqp` fixture, harness-T22), the
real `TestHarnessTopology` over it, `ScriptedHarnessInstance` (`tests/fakes/harness_instance.py`,
harness-T13), `InMemoryTestRunStore` (the module lane fakes-test-harness created), `FakeClock` and
`RecordingLogger` (`tests/fakes/system.py`, `tests/fakes/observability.py`, lane fakes-observability):
- [ ] A request is handled; its answer is published to its reply queue with the right correlation id; the delivery is completed.
- [ ] A dead-letter outcome moves the message to the dead queue.
- [ ] A malformed request is dead-lettered and logged with its message id.
- [ ] `reconcile` turns an unrecorded dead message into a dead letter and an answer, completes one already recorded, and keeps an undecodable one as malformed.
- [ ] `stop` abandons an in-flight run (`ScriptedHarnessInstance(block_until_abandoned=True)`), and the message is requeued with its delivery count incremented.
- [ ] A request without `reply_to` is handled and completed with no publish.
- [ ] 100% coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/test_harness/test_amqp_service.py` (`from vibey.infrastructure.test_harness import amqp_service as svc`):
- `test_handles_replies_and_completes`
- `test_dead_letter_outcome_moves_the_message`
- `test_malformed_request_is_dead_lettered`
- `test_reconcile_records_an_unrecorded_dead_message`
- `test_reconcile_completes_a_recorded_one`
- `test_reconcile_keeps_undecodable_messages`
- `test_reconcile_runs_on_its_interval` (a small interval; `stop` cancels it)
- `test_stop_abandons_and_requeues`
- `test_missing_reply_to_is_skipped`
- `test_a_failed_reply_is_logged_not_raised`
- `test_service_satisfies_its_interface`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_harness tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The requester (harness-T24) and the `serve` command (harness-T25).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** rmq-r04-bootstrap-amqp, harness-T13-harness-instance, harness-T22-harness-topology, fakes-test-harness (`InMemoryTestRunStore`), fakes-observability (`FakeClock`, `RecordingLogger`).
- **Files touched:** the two new source files and the new test file.
- **Shares a file with:** none.
- **Must keep passing unchanged:** harness-T13's and T22's tests, `tests/fakes/*`, and the protected tests.
- **Registry (amendment A4):** nothing new. The service is built by the composition (harness-T25b) and never substituted; the fake composition builds the real service over the in-memory broker.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - In test files import modules, not `Test*` names (`svc.TestHarnessService`).
  - Substitute only at a declared seam (the constructor keywords). Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - No lane needs a running RabbitMQ (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out). No test waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
