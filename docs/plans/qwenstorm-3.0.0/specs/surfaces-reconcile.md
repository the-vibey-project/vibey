## Title
feat(surfaces): the lane drains its dead queue into surface_dead_letter rows — written once, guarded operations parked, parks ledgered

## Why
Draft ADR-0047 §9 (`specs/ADR-surface-lanes.md`, "The park"): "Every
`reconcile_interval_seconds` (default 30), the lane drains its dead queue into
`surface_dead_letter` rows. A row is written once, keyed by `(surface, dedupe_key)`. For a
guarded operation, the drain also moves `surface_operation` to `parked`, so any later request
with that `op_id` is answered `parked` at once. **Nothing waits for a human**, and nothing is
retried forever." "A dead letter drained from the broker is acknowledged, which removes the
value from the broker too" ("Security impact"). Sub-doctrine 8.f: parked "with its evidence,
never retried forever and never dropped". 7.c: the park is written to the ledger when the
operation served a project. ADR-0047 lane S25.

The dead queue holds two kinds of message: the lane's own evidence (`type = "surface.dead"`),
and requests the broker dead-lettered (a malformed or wrong-surface message the lane rejected,
or one that hit the queue's delivery limit). Classifying the second kind by its body, not by
the broker's `x-death` header, keeps the in-memory broker and RabbitMQ equivalent.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/reconcile.py`, `class SurfaceDeadLetterReconciler`:

1. `__init__(self, *, surface: SurfaceName, client: AmqpClientInterface, names: SurfaceQueueNamesInterface, dead_letters: SurfaceDeadLetterRepositoryInterface, operations: SurfaceOperationRepositoryInterface, recorder: SurfaceLedgerRecorderInterface, settings: SurfacesConfigInterface, clock: Clock, logger: Logger, instance: str, codec=SURFACE_PROTOCOL, redactor=SURFACE_REDACTOR, catalogue=CATALOGUE)`.
2. `async drain(self) -> int`: up to `settings.dead_drain_batch` times,
   `d = await client.get(names.dead_queue(surface))`, stopping at `None`. For each:
   1. **Evidence** (`d.properties.type == "surface.dead"`): `dead = codec.dead_from_bytes(d.body)`;
      `dedupe_key = d.properties.message_id or dead.message_id`.
   2. **A dead-lettered request** (anything else) whose body decodes as a request: reason
      `WRONG_SURFACE` when its surface is not this lane's, else `DELIVERY_LIMIT`; build a
      `SurfaceDeadLetter` with `detail` naming the reason, `attempts=0`,
      `delivery_count=d.delivery_count`, `instance`, `dead_lettered_at=clock.now()`, the
      request encoded with its args redacted by `redactor.for_dead_letter` (its `retained` too);
      `dedupe_key = f"{request.request_id}:{reason.value}"`.
   3. **Undecodable**: reason `MALFORMED`; `surface`/`operation`/`op_id`/`request_id` are this
      surface, `"?"`, `"?"`, and `d.properties.message_id or "sha256:<hex of the body>"`;
      `request = {"bytes": len(d.body), "sha256": <hex>}` (never the body), `retained=False`;
      `dedupe_key = f"sha256:<hex>:malformed"`.
   4. `inserted = await dead_letters.record(SurfaceDeadLetterEntry(...))`.
   5. When inserted, the operation is `GUARDED` and a `surface_operation` row exists for
      `(surface, op_id)` in any state but `done`: `operations.finish(state=PARKED, detail=dead.detail)`
      (ADR §9: "any later request with that `op_id` is answered `parked` at once"; a `done`
      row is left alone, since its effect is recorded).
   6. When inserted and the request carried a project:
      `await recorder.record_parked(dead, caller)` (a malformed message has none).
   7. `await d.complete()`.
   An exception in steps 1–6 (a repository error, for instance) logs
   `surface.dead_letter_drain_failed` at `error`, `await d.abandon()` (it stays in the queue),
   and ends this drain early. Returns how many were completed.
3. After a drain that did anything, log `surface.dead_letters_drained` at `info` with `drained`,
   `recorded` (new rows), `duplicates`, `malformed` and `elapsed_ms` (8.g).
4. **Interface** `surface_lanes/interfaces/reconcile_interface.py`:
   `@runtime_checkable class SurfaceDeadLetterReconcilerInterface(Protocol)` with `drain`;
   exported. Registry: the real class over `InMemoryAmqpClient` and the in-memory stores and
   recorder, in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/reconcile.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/reconcile_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_reconcile.py` and
  `tests/infrastructure/surface_lanes/test_reconcile_integration.py`.

## Acceptance criteria
- [ ] An evidence message becomes one row with the evidence's fields; draining the same evidence twice (published twice) writes one row and completes both.
- [ ] A guarded send's `started` or `failed` row moves to `parked` when its evidence is drained, a `done` row does not, and a later request with that `op_id` is answered `parked` by `SurfaceGuardedExecutor`.
- [ ] A request dead-lettered by the delivery limit (`memory_amqp` with `x-delivery-limit`, driven with `simulate_channel_close`) becomes a `delivery_limit` row; a wrong-surface one a `wrong_surface` row.
- [ ] A malformed body becomes a `malformed` row holding only its length and digest.
- [ ] A secret argument is stored as a digest and the row is not `retained`; an email's body is stored and the row is `retained`.
- [ ] A repository failure (`fail_next`) abandons that message, stops the drain, and a later drain records it.
- [ ] The drain stops at `dead_drain_batch`; a project park lands in `InMemoryLedger` as `SurfaceOperationParked`.
- [ ] Integration (`amqp_url`): a message dead-lettered by a real quorum queue's delivery limit reaches the dead queue and is drained as `delivery_limit` (the ADR's *Verification owed* item 7; also record the `x-death` reason the broker set, as evidence, in the commit body).
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_reconcile.py` (no service):
- `test_evidence_becomes_one_row`
- `test_the_same_evidence_twice_is_one_row`
- `test_a_guarded_unknown_outcome_is_parked`
- `test_a_delivery_limit_request_is_recorded`
- `test_a_wrong_surface_request_is_recorded`
- `test_a_malformed_body_keeps_only_its_digest`
- `test_secrets_are_digested_and_sends_are_retained`
- `test_a_repository_failure_abandons_and_stops`
- `test_the_drain_is_bounded`
- `test_a_project_park_is_ledgered`
- `test_reconciler_satisfies_its_interface`
`tests/infrastructure/surface_lanes/test_reconcile_integration.py` (`amqp_url`):
- `test_a_real_delivery_limit_dead_letter_is_drained`

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
- The reconcile tick (`surfaces-lane-host`); reading and answering rows (`surfaces-cli-dead-letters`,
  `surfaces-requeue`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-dispatcher` (evidence messages in tests), `surfaces-records-fakes`, `surfaces-ledger-recorder`, `surfaces-config` (`dead_drain_batch`).
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
