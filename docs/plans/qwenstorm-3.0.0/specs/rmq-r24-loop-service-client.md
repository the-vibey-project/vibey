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

## Lane card
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
