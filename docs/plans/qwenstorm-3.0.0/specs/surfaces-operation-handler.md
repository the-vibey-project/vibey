## Title
feat(surfaces): SurfaceOperationHandler runs one validated request on its adapter — start_by, bound, retries, and an exact outcome

## Why
Draft ADR-0047 §6 (`specs/ADR-surface-lanes.md`): "The lane refuses to start an operation after
its `start_by`. It answers `expired` instead. Once it has started an operation,
`operation_timeout_seconds` (default 60) bounds it." §8 retries by idempotency class (lane
`surfaces-failure-policy`); §3's `create_config` row: "On failure, the lane reads
`get_config(key)`; the stored value equal to the requested one means a replayed create, which
succeeded." "Security impact": "The operation names a method from a fixed table, never an
attribute taken from a message." And a native backend deduplicates by the `op_id` the lane
passes (§8 table: "`op_id` given to the backend").

This class is the core of every surface lane except the cache's reads (`surfaces-cache-handler`)
and the guard around three sends (`surfaces-guarded-execution`), which both wrap or replace it
behind the same `SurfaceExecutorInterface`. ADR-0047 lane S18.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/handler.py`:

1. `@dataclass(frozen=True, slots=True) class OperationOutcome`: `status: ReplyStatus`,
   `result: object = None` (a wire result), `detail: str = ""`, `attempts: int = 0`,
   `dead_reason: DeadLetterReason | None = None` (what a dead letter would say, when one is
   owed), `replayed: bool = False`, `started_at: datetime | None = None`,
   `finished_at: datetime | None = None`.
2. `class SurfaceOperationHandler`:
   `__init__(self, *, adapter: object, settings: SurfacesConfigInterface, clock: Clock, policy: SurfaceFailurePolicyInterface = FAILURE_POLICY, args: SurfaceArgsCodecInterface = SURFACE_ARGS, catalogue: SurfaceCatalogueInterface = CATALOGUE, codec: SurfaceProtocolCodecInterface = SURFACE_PROTOCOL, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep)`.
   `async execute(self, request: SurfaceRequest) -> OperationOutcome`:
   1. `spec = catalogue.get(request.surface, request.operation)`; `_ping` raises `ValueError`
      (the dispatcher answers it).
   2. `now = clock.now()`. If `now > request.start_by`: return `EXPIRED`,
      `detail=f"not started: its start_by {request.start_by.isoformat()} had passed"`,
      `dead_reason=EXPIRED`, `finished_at=now`. Nothing is called.
   3. `kwargs = args.from_wire(spec, request.args)`; a `MalformedSurfaceMessage` returns
      `REJECTED` with its text and `dead_reason=MALFORMED`. When `spec.accepts_key`,
      `kwargs["idempotency_key"] = request.op_id` — always, so a redelivery of the same request
      reaches a native backend with the same key.
   4. `method = getattr(self._adapter, spec.operation)` (the catalogue's name only).
   5. Run through `policy.retry_for(spec, settings, sleep=sleep).call(...)`, each attempt
      `await asyncio.wait_for(method(**kwargs), settings.operation_timeout_seconds)`, counting
      attempts.
   6. Success: `OK`, `result=args.result_to_wire(spec, value)`, `attempts`, `started_at=now`,
      `finished_at=clock.now()`.
   7. Failure (`Exception`, never `BaseException`), `verdict = policy.classify(spec, exc)`:
      - **`create_config` readback** first: unless the verdict is `NOT_FOUND`, call
        `get_config(key)` once under the same bound; if it returns the requested value, the
        outcome is `OK` with `replayed=True` and `detail="replayed create: the stored value already matches"`.
        A failing readback is ignored and the original failure is reported.
      - `NOT_FOUND` → `NOT_FOUND`, `detail=str(exc)`, no dead reason.
      - `OUTCOME_UNKNOWN` → `PARKED`, `dead_reason=OUTCOME_UNKNOWN`.
      - `RETRY` (the retries ran out) → `ERROR`, `dead_reason=RETRIES_EXHAUSTED`.
      - `PERMANENT` → `ERROR`, `dead_reason=FAILED`.
      The detail is `codec.clip(f"{type(exc).__name__}: {exc}")`, except that a
      `TimeoutError` says `f"timed out after {settings.operation_timeout_seconds}s; it may still apply"`
      (ADR "Consequences").
3. `src/vibey/infrastructure/surface_lanes/interfaces/handler_interface.py`:
   `@runtime_checkable class SurfaceExecutorInterface(Protocol)` with
   `async execute(self, request) -> OperationOutcome` (types under `TYPE_CHECKING`), and
   `SurfaceOperationHandlerInterface(SurfaceExecutorInterface, Protocol)`; both exported.
4. **Registry.** `SurfaceExecutorInterface → functools.partial(SurfaceOperationHandler, adapter=InMemoryTracker(), settings=SurfacesConfig(), clock=FakeClock())`
   (the real class over an in-memory adapter), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/handler.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/handler_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_handler.py`.

## Acceptance criteria
- [ ] A request past its `start_by` (by a `FakeClock`) returns `expired` and calls nothing.
- [ ] `tracker.create_ticket` reaches `InMemoryTracker` with `idempotency_key == op_id`, so executing the same request twice returns one ticket id.
- [ ] A Plane adapter over `InMemoryHttpServer` answering 503 then 201 succeeds on attempt 2, with the injected sleep recording the first backoff.
- [ ] A read that raises a transport error is `error` after one attempt; `KeyError` is `not_found` for `secrets.get_secret`.
- [ ] A guarded `docs.create_page` whose adapter raises `TimeoutError` is `parked` with `dead_reason=outcome_unknown`; one raising `URLError(ConnectionRefusedError())` then succeeding is `ok` after 2 attempts.
- [ ] `create_config` that raises after storing (a small port class in the test that stores then raises) is `ok` and `replayed`.
- [ ] An adapter that sleeps past `operation_timeout_seconds=1` (with `retry_backoff_seconds=()`) is `error` with the "may still apply" detail.
- [ ] Bad typed arguments are `rejected` with `dead_reason=malformed`; `_ping` raises `ValueError`.
- [ ] 100% `infrastructure/` branch coverage; the parity test passes.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_handler.py` (no service; `FakeClock`, an instant sleep class, the production `InMemory*` adapters, the real Plane adapter over `InMemoryHttpServer`, and small port classes in the module that raise on cue — declared-seam fakes, not mocks):
- `test_a_request_past_start_by_expires_without_a_call`
- `test_native_operations_pass_the_op_id_as_the_key`
- `test_overwrite_retries_a_503_then_succeeds`
- `test_reads_are_never_retried`
- `test_not_found_is_an_answer`
- `test_guarded_timeout_parks_with_outcome_unknown`
- `test_guarded_connection_refused_is_retried`
- `test_create_config_readback_turns_a_replay_into_success`
- `test_the_operation_bound_reports_it_may_still_apply`
- `test_bad_arguments_are_rejected_as_malformed`
- `test_ping_is_not_the_handlers`
- `test_handler_satisfies_its_interfaces`

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
- The intent record around guarded sends (`surfaces-guarded-execution`); the cache's memo and
  batching (`surfaces-cache-handler`); replying and dead-lettering (`surfaces-dispatcher`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-failure-policy`, `surfaces-args-codec`, `surfaces-protocol`, `fakes-observability` (`FakeClock`), and the adapter lanes whose `idempotency_key` it passes: `surfaces-adapter-tracker`, `surfaces-adapter-docs`, `surfaces-adapter-messaging`, `surfaces-adapter-siem`, `surfaces-adapter-email`, `surfaces-adapter-sms`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam (the adapter, clock and sleep are injected); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
