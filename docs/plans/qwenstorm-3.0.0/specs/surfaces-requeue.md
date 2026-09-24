## Title
feat(surfaces): SurfaceRequeuer grants a parked operation — it republishes the retained request once, marks the dead letter answered, and ledgers the grant

## Why
Draft ADR-0047 §9 (`specs/ADR-surface-lanes.md`, "The grant"): "`vibey surface requeue <id>`
republishes a retained request with `grant: true` and a new `request_id`. It then marks the row
answered, once. The dead letter itself is never rewritten. A request that is not retained (it
carried a secret or bytes) cannot be requeued from its row, and the command says so and names the
caller as the only place the value exists." This is ADR-0024's grant pattern, and non-negotiable
1: a parked operation never blocks a worker; a person decides later. Publishing **before**
marking is safe, because a guarded operation answers a duplicate grant from its record
(`surfaces-guarded-execution`: a grant re-runs only a `parked` or `failed` row) and native ones
are deduplicated by their backend. 7.c: the grant is ledgered when the operation served a
project. Part of ADR-0047 lane S28.

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/requeue.py`:

1. `@dataclass(frozen=True, slots=True) class RequeueResult`: `dead_letter_id: UUID`,
   `surface: str`, `operation: str`, `op_id: str`, `request_id: str` (the new one).
2. `class RequeueRefused(VibeyError)` with `reason: str`; `__str__` is the reason.
3. `class SurfaceRequeuer`,
   `__init__(self, *, dead_letters: SurfaceDeadLetterRepositoryInterface, client: AmqpClientInterface, topology: SurfaceLaneTopologyInterface, names: SurfaceQueueNamesInterface, settings: SurfacesConfigInterface, recorder: SurfaceLedgerRecorderInterface, clock: Clock, codec=SURFACE_PROTOCOL, catalogue=CATALOGUE, new_id: Callable[[], UUID] = uuid4)`.
   `async requeue(self, dead_letter_id: UUID, *, answered_by: str) -> RequeueResult`:
   1. `row = await dead_letters.get(dead_letter_id)`; `None` → `RequeueRefused(f"no dead letter {dead_letter_id}")`.
   2. Answered → `RequeueRefused(f"dead letter {id} was already answered at {row.answered_at.isoformat()} by {row.answered_by}")`.
   3. Not `retained` → `RequeueRefused(f"dead letter {id} did not keep its request (it carried a secret or bytes); only the caller that made {row.surface}.{row.operation} (op {row.op_id}) holds the value — repeat the call there")`.
   4. `request = codec.decode_request(row.request)` (a `MalformedSurfaceMessage` →
      `RequeueRefused("the stored request is not a valid surface request")`). A reason of
      `malformed` or `wrong_surface` is refused the same way (nothing valid to grant).
   5. Build the grant: `dataclasses.replace(request, request_id=str(new_id()), requested_at=now, start_by=now + window, grant=True)`,
      where the window is `send_start_by_seconds` for a send and `write_timeout_seconds`
      otherwise; the `op_id` and the caller are kept.
   6. `await topology.declare(surface)`; publish `codec.request_to_bytes(grant)` to
      `names.request_exchange()` with `names.write_key(surface)`,
      `AmqpProperties(message_id=grant.request_id, correlation_id=grant.request_id, type="surface.request", delivery_mode=2)`
      (no `reply_to`: nobody waits; the outcome shows in the ledger and in dead letters),
      `mandatory=True, confirm=True`. A failure raises
      `RequeueRefused(f"the bus refused the grant: {exc}; nothing was marked")`.
   7. `await dead_letters.mark_answered(id, answered_by=answered_by, requeue_request_id=grant.request_id, at=now)`;
      if it returns False (raced), raise `RequeueRefused("another person answered it first; the grant was published and is answered from the operation's record")`.
   8. `await recorder.record_requeued(...)` with the request's caller.
   9. Return the result. An empty `answered_by` raises `ValueError`.
4. **Interface** `surface_lanes/interfaces/requeue_interface.py`:
   `@runtime_checkable class SurfaceRequeuerInterface(Protocol)` with `requeue`; exported.
   Registry: the real class over the in-memory stores, `InMemoryAmqpClient` and the in-memory
   recorder, in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/requeue.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/requeue_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_requeue.py`.

## Acceptance criteria
- [ ] A retained `email.send_email` dead letter is republished once with `grant: true`, a new `request_id`, the same `op_id` and caller; the row is answered with `requeue_request_id` set; the evidence columns are unchanged.
- [ ] Running the granted request through a lane (a `SurfaceGuardedExecutor` over the same in-memory store, row `parked`) sends exactly one email; a second, raced grant is answered from the record and sends nothing.
- [ ] Unknown, answered, not-retained, malformed and wrong-surface rows are refused with the messages above; the not-retained message names the surface, operation and op id.
- [ ] A refused publish marks nothing.
- [ ] A project grant lands in `InMemoryLedger` as `SurfaceOperationRequeued`.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_requeue.py` (no service; `memory_amqp`, `InMemorySurfaceDeadLetterRepository`, `InMemorySurfaceOperationRepository`, `InMemoryLedger`, `InMemoryProjectRepository`, `FakeClock`):
- `test_a_retained_send_is_granted_once`
- `test_the_grant_sends_once_through_the_guard`
- `test_refusals_name_their_reason` (parametrized)
- `test_a_refused_publish_marks_nothing`
- `test_the_grant_is_ledgered`
- `test_requeuer_satisfies_its_interface`

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
- The CLI (`surfaces-cli-dead-letters`); per-caller broker users (a follow-up in "Security
  impact"). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the Title
  as the subject.

## Lane card
- **Depends on:** `surfaces-reconcile`, `surfaces-guarded-execution`, `surfaces-topology`, `surfaces-ledger-recorder`, `surfaces-records-fakes`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Never block a worker on a human: nothing here waits for anyone.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
