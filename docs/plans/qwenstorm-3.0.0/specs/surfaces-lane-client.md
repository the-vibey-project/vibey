## Title
feat(surfaces): SurfaceLaneClient puts one operation on its surface's queue, waits for the answer within a bound, and never falls back

## Why
Draft ADR-0047 §6–§7 (`specs/ADR-surface-lanes.md`) define the caller's side of a surface lane:
build a request with a fresh `request_id` and an `op_id` (the caller's idempotency key or a
fresh id), a `start_by` window, publish a read unconfirmed to the classic read queue and
anything else confirmed to the quorum write queue, and wait for the reply "for at most
`(start_by − now) + operation_timeout_seconds + 1 s`". A send (`accept` mode) returns once the
broker has confirmed a persistent publish. The table "What the caller sees" fixes every error;
"the caller never falls back to calling the backend directly. That would be a second path to
the surface, which is what 8.f forbids." A request whose encoded body exceeds
`inline_max_bytes` is refused **before** it is published (§5). ADR-0047 lane S16.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/client.py`, `class SurfaceLaneClient`:

1. `__init__(self, *, client: AmqpClientInterface, topology: SurfaceLaneTopologyInterface, router: SurfaceReplyRouterInterface, names: SurfaceQueueNamesInterface, settings: SurfacesConfigInterface, clock: Clock, caller: SurfaceCallerScopeInterface, catalogue: SurfaceCatalogueInterface = CATALOGUE, args: SurfaceArgsCodecInterface = SURFACE_ARGS, codec: SurfaceProtocolCodecInterface = SURFACE_PROTOCOL, new_id: Callable[[], UUID] = uuid4)`.
2. `async call(self, surface: SurfaceName, operation: str, arguments: Mapping[str, object], *, idempotency_key: str | None = None) -> object`:
   1. `spec = catalogue.get(surface, operation)`; `wire = args.to_wire(spec, arguments)`
      (a `ValueError` propagates: a caller's bug).
   2. `request_id = str(new_id())`; `op_id = idempotency_key or str(new_id())`. A key that does
      not match `ID_PATTERN` raises `ValueError` naming the pattern.
   3. `now = clock.now()`; the window is `read_timeout_seconds` for a read,
      `send_start_by_seconds` for a send, `write_timeout_seconds` otherwise;
      `start_by = now + window`.
   4. `request = SurfaceRequest(request_id, op_id, surface, operation, wire, now, start_by, caller.current())`;
      `body = codec.request_to_bytes(request)`; when `len(body) > settings.inline_max_bytes`
      raise `SurfacePayloadTooLarge(surface.value, operation, len(body), settings.inline_max_bytes)`.
   5. `await topology.declare(surface)`; an `AmqpError` (or `OSError`) becomes
      `SurfaceLaneUnavailable(surface.value, f"the bus is unreachable: {exc}")`.
   6. Properties: `AmqpProperties(message_id=request_id, correlation_id=request_id, type="surface.request", reply_to=…, delivery_mode=…)`.
      - **read**: `reply_to = await router.reply_to()`, `fut = router.expect(request_id)`,
        publish to `names.request_exchange()` with `names.read_key(surface)`,
        `delivery_mode=1`, `mandatory=False, confirm=False`.
      - **send** with `settings.sends_await_outcome` false: no `reply_to`; publish persistent
        (`delivery_mode=2`) with `names.write_key(surface)`, `mandatory=True, confirm=True`,
        and return `None` once it is confirmed.
      - **everything else** (answer, ack, and a send when `sends_await_outcome` is true):
        `reply_to` and `expect` as for a read; publish persistent and confirmed to the write key.
      A publish error (`AmqpPublishError` for a nack or a full `reject-publish` queue, any
      `AmqpError`, `OSError`) forgets the future and raises
      `SurfaceLaneUnavailable(surface.value, f"the broker refused the request: {exc}")`.
   7. Wait: `timeout = (start_by - clock.now()).total_seconds() + settings.operation_timeout_seconds + 1`,
      `reply = await asyncio.wait_for(fut, timeout)`. On timeout forget the future and raise
      `SurfaceLaneUnavailable(surface.value, f"no reply within {timeout:.0f}s; no lane started {surface.value}.{operation} before its start_by, so it was not applied")`.
   8. Map the reply:
      - `ok` → `args.result_from_wire(spec, reply.result)`;
      - `not_found` → `KeyError(reply.detail)` or `FileNotFoundError(reply.detail)` by
        `spec.not_found`; `RuntimeError(reply.detail)` if the spec has none;
      - `error` → `RuntimeError(f"{surface.value}.{operation} failed in its lane: {reply.detail}")`;
      - `rejected` → `ValueError(reply.detail)` (an idempotency key reused with other arguments);
      - `expired` → `SurfaceLaneUnavailable(surface.value, f"the lane refused it after its start_by: {reply.detail}")`;
      - `parked` → `SurfaceOperationParked(surface.value, operation, op_id)`.
3. `async ping(self, surface: SurfaceName) -> Mapping[str, object]`: `call(surface, PING_OPERATION, {})`.
4. `async close(self) -> None`: `await router.close()`.
5. `src/vibey/infrastructure/surface_lanes/interfaces/client_interface.py`:
   `@runtime_checkable class SurfaceLaneClientInterface(Protocol)` with `call`, `ping`, `close`;
   exported from the interfaces `__init__.py`.
6. **The fake.** New `tests/fakes/surface_lanes.py` with `class RecordingSurfaceLaneClient`
   (implements `SurfaceLaneClientInterface`): records each call as
   `(surface, operation, dict(arguments), idempotency_key)` in `calls`; answers from
   `script: dict[tuple[SurfaceName, str], list[object]]` (consumed in order, the last repeats;
   an `Exception` instance in the script is raised); an unscripted call returns `None`;
   `ping` returns `{"surface": surface.value, "instance": "fake"}`. Register it for
   `SurfaceLaneClientInterface` and add the interface to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/client.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/client_interface.py`; interfaces
  `__init__.py`; new `tests/fakes/surface_lanes.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_client.py` and
  `tests/infrastructure/surface_lanes/test_client_integration.py`.

## Acceptance criteria
- [ ] Against `memory_amqp` with a scripted responder in the test (a small class consuming the write/read queue and publishing replies to `reply_to` through the default exchange): a read goes unconfirmed to `vibey.surface.cache.read` with `delivery_mode=1`; an answer goes confirmed and persistent to the write queue; both return the decoded result.
- [ ] A send returns after the confirm with no `reply_to`; with `sends_await_outcome=True` it waits for a reply.
- [ ] Every row of ADR §6's table: each reply status maps to its exception; a full `reject-publish` write queue raises `SurfaceLaneUnavailable` at once; a responder that never answers raises `SurfaceLaneUnavailable` after the bound computed from a `FakeClock` (use `read_timeout_seconds=1` and `operation_timeout_seconds=1` so the test stays under 5 s); an oversize request raises `SurfacePayloadTooLarge` and publishes nothing.
- [ ] The request's `caller` is the scope's current caller (bind a project in the test and read it off the published body).
- [ ] With an idempotency key, `op_id` is the key; without, a fresh id; a key outside `ID_PATTERN` is refused.
- [ ] Integration (`amqp_url`): a publish to a full real `reject-publish` write queue raises `SurfaceLaneUnavailable` (the ADR's *Verification owed* item 4 through the client).
- [ ] The fakes parity test passes; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_client.py` (no service):
- `test_a_read_is_published_unconfirmed_and_transient_to_the_read_queue`
- `test_an_answer_is_published_confirmed_and_persistent_and_returns_the_result`
- `test_a_send_returns_after_the_confirm_without_a_reply_queue`
- `test_sends_await_outcome_waits_for_the_reply`
- `test_each_reply_status_maps_to_its_exception` (parametrized)
- `test_a_full_write_queue_is_unavailable_at_once`
- `test_no_reply_within_the_bound_is_unavailable`
- `test_an_oversize_request_is_refused_before_publishing`
- `test_the_caller_scope_rides_in_the_request`
- `test_the_idempotency_key_becomes_the_op_id`
- `test_ping_is_an_answered_read`
- `test_client_satisfies_its_interface`
`tests/infrastructure/surface_lanes/test_client_integration.py` (`amqp_url`):
- `test_a_full_real_write_queue_is_unavailable`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes tests/fakes tests/meta
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The lane side (`surfaces-dispatcher`, `surfaces-lane-host`); the port adapters over this client
  (`surfaces-queued-*`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill
  trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-topology`, `surfaces-reply-router`, `surfaces-args-codec`, `fakes-observability` (`FakeClock`).
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`. A fake under `tests/fakes/` never imports `unittest.mock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
