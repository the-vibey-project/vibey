## Title
feat(surfaces): every surface lane measures each operation and, each interval, its throughput, latency, queue depth and consumers

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md`, "8.g — always measured"): "Every
loop, lane, queue, surface, test run and model records its latency, throughput, queue depth and
waiting time, resource use and outcome as it works, continuously and in real time … A component
that cannot report its measurements is incomplete." `issue-audit/gaps.md` D1 records that
"Surfaces … record nothing". Draft ADR-0047 §10 and §15 also owe a measured cache cost before
the default flips; the per-operation numbers here are that measurement's live counterpart, and
`surfaces-bench` is its controlled one.

A lane's queue depth and consumer count come from a **passive queue declare**. Three lanes of
three ADRs need that from `vibey_bootstrap.amqp` (ADR-0045 T21: consumer count; ADR-0046 L21:
queue depth; ADR-0047: both, here). They share **one** method, owned by ADR-0045's T21 pair —
`harness-T21a-amqp-consumer-count-client` (the aio-pika method) and
`harness-T21-amqp-consumer-count` (the interface and the in-memory method), `specs/harness-queue.txt`
— which must land as below, **not** as the `consumer_count(queue) -> int | None` those two
specs name today (they need that one amendment; everything else in them stands):

```python
# vibey_bootstrap/amqp/properties.py
@dataclass(frozen=True, slots=True)
class AmqpQueueState:
    name: str
    message_count: int   # ready messages; unacknowledged deliveries are not counted
    consumer_count: int

# vibey_bootstrap/amqp/interfaces/client_interface.py (AmqpClientInterface)
async def inspect_queue(self, queue: str) -> AmqpQueueState | None: ...
```

`AmqpClient.inspect_queue` opens a temporary channel, runs
`channel.declare_queue(queue, passive=True)`, returns
`AmqpQueueState(queue, declaration_result.message_count, declaration_result.consumer_count)`,
maps `aio_pika.exceptions.ChannelNotFoundEntity` to `None`, and always closes the temporary
channel. `InMemoryAmqpClient.inspect_queue` returns the ready count and the active consumers of
a declared queue, `None` for an undeclared one. The harness's consumer count (T21, T24) is
`inspect_queue(q).consumer_count` and ADR-0046 L21's (`loops-queue-depth`) queue depth is
`inspect_queue(q).message_count`; neither adds a second passive declare, and L21 adds only
exclusive consume. Where the family also records measurements, this lane
uses the family's latency histogram (`vibey_bootstrap.tracing`, 10.e).

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/meter.py`:

1. **Precondition.** `grep -n "async def inspect_queue" src/vibey_tools/bootstrap/vibey_bootstrap/amqp/interfaces/client_interface.py`
   must print one line. If it does not, stop and report (the T21 pair has not landed in its
   shared form); do not add a passive declare here.
2. `class FamilyLatencyRecorder`: `record(self, operation: str, seconds: float, *, error: bool) -> None`
   calls `vibey_bootstrap.tracing._record_latency(operation, seconds, error=error, slow=False)`
   (exported in `vibey_bootstrap.tracing.__all__`), so `build_metrics_snapshot()` shows surface
   latencies. `FAMILY_LATENCY: Final[LatencyRecorderInterface] = FamilyLatencyRecorder()`.
3. `class SurfaceLaneMeter`:
   `__init__(self, *, surface: SurfaceName, instance: str, logger: Logger, clock: Clock, latency: LatencyRecorderInterface = FAMILY_LATENCY)`.
   - `observe(self, request: SurfaceRequest, outcome: OperationOutcome) -> None`: logs
     `surface.operation` at `info` with `surface`, `operation`, `status`, `attempts`,
     `replayed`, `instance`, `wait_ms` and `service_ms` (as `surfaces-ledger-recorder` computes
     them, `None` when a time is missing), and **never** an argument or a result. It records
     `latency.record(f"surface.{surface}.{operation}", service_seconds, error=status not in ("ok", "not_found"))`
     when the outcome has both times, and accumulates the interval's counts by status and
     its wait and service samples.
   - `observe_malformed(self) -> None`: counts a malformed or wrong-surface delivery.
   - `async flush(self, client: AmqpClientInterface, queues: Mapping[str, str], cache: CacheLaneHandlerInterface | None = None) -> Mapping[str, object]`:
     for each `label → queue name` in `queues` (the host passes `write`, `read`, `dead`),
     `await client.inspect_queue(name)` (an exception or `None` gives `None` for that queue);
     reads and resets `cache.stats()` when given; then logs `surface.lane.measured` at `info`
     with exactly: `surface`, `instance`, `interval_seconds`, `operations`, `by_status`
     (dict), `malformed`, `throughput_per_second`, `wait_ms_p50/p95/p99`,
     `service_ms_p50/p95/p99` (nearest-rank; `None` when empty), `<label>_depth` and
     `<label>_consumers` for each queue, and, for the cache lane, `memo_hits`, `memo_misses`,
     `batches`, `batched_reads`. It resets the interval and returns the logged mapping.
4. **Interfaces** in `surface_lanes/interfaces/meter_interface.py`:
   `LatencyRecorderInterface` and `SurfaceLaneMeterInterface`, exported. Registry:
   `SurfaceLaneMeterInterface → functools.partial(SurfaceLaneMeter, surface=SurfaceName.CACHE, instance="fake", logger=RecordingLogger(), clock=FakeClock(), latency=<a recording LatencyRecorder in tests/fakes/surface_lanes.py>)`,
   and `LatencyRecorderInterface → RecordingLatencyRecorder` (new, in `tests/fakes/surface_lanes.py`,
   recording `(operation, seconds, error)`); both in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/meter.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/meter_interface.py`; interfaces
  `__init__.py`; `tests/fakes/surface_lanes.py` (append `RecordingLatencyRecorder`);
  `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_meter.py`.

## Acceptance criteria
- [ ] Observing an `ok` operation logs `surface.operation` with its wait and service times and no argument or result field; the latency recorder gets `surface.cache.get`.
- [ ] After ten observations over a `FakeClock` interval of 10 s, `flush` logs `operations=10`, `throughput_per_second=1.0`, the percentiles, `by_status`, and each queue's depth and consumers read from `memory_amqp.inspect_queue`; a second flush starts from zero.
- [ ] A queue whose inspection raises or is undeclared reports `None` depth; the flush still logs.
- [ ] For the cache lane the memo counters appear and are reset.
- [ ] `FamilyLatencyRecorder` makes the operation appear in `vibey_bootstrap.tracing.latency_snapshot()`.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_meter.py` (no service; `memory_amqp`, `RecordingLogger`, `FakeClock`, `RecordingLatencyRecorder`):
- `test_an_operation_is_logged_without_its_values`
- `test_flush_reports_throughput_latency_depth_and_consumers`
- `test_flush_resets_the_interval`
- `test_an_uninspectable_queue_reports_none`
- `test_cache_memo_counters_are_reported_and_reset`
- `test_family_latency_recorder_feeds_the_family_histogram`
- `test_meter_satisfies_its_interfaces`

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
- `inspect_queue` itself (T21 owns it). Resource use per process (the 8.g epic, gaps D1) and a
  deployment-scoped measurement ledger. CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change remotes.
  Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-cache-handler` (`CacheLaneHandlerInterface`), `surfaces-operation-handler`, `surfaces-lane-client` (creates `tests/fakes/surface_lanes.py`), `harness-T21-amqp-consumer-count` (the shared `inspect_queue`), `fakes-observability`.
- **Shares a file with:** `tests/fakes/surface_lanes.py`, `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, the vibey-bootstrap tracing tests, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `STORM/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
