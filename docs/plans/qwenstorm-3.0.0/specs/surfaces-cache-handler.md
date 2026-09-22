## Title
feat(surfaces): the cache lane batches concurrent reads into one Valkey pipeline and serves hits from a coherent read-through memo

## Why
Draft ADR-0047 §10 (`specs/ADR-surface-lanes.md`, "The cache, honestly") keeps 8.f's rule for
the cache — "The cache is no exception" (`src/vibey_tools/gh/docs/doctrines.md`, 8.f) —
without making it pointless:

- **Concurrent reads are batched.** "Every read the lane has buffered (up to `read_prefetch`)
  that is waiting in the same event-loop turn goes to Redis in one pipeline of `GET` and
  `PTTL`. There is no timer, so batching adds no latency when there is only one reader."
- **The lane owns a read-through memo** (the family's `BoundedTtlMemo`, lane `surfaces-memo`):
  coherent because the lane is the only writer of vibey's cache keys; "a memo entry never
  outlives Redis's own expiry, which is read with `PTTL` on every fill"; "a read that raced a
  write is never memoized: every write bumps a generation counter, and a fill is discarded if
  the counter moved while the read was in flight."
- The precondition is stated, not assumed: nothing else writes vibey's cache database (db 0;
  Plane uses db 1, `deploy/helm/vibey/templates/plane.yaml:21`).

It also feeds 8.g: hits, misses and batch sizes are what `surfaces-lane-meter` reports and
`surfaces-bench` measures. ADR-0047 lane S19. The server is Valkey (the operator's ruling).

## Required behaviour
In the new `src/vibey/infrastructure/surface_lanes/cache_handler.py`, `class CacheLaneHandler`
(implements `SurfaceExecutorInterface`):

1. `__init__(self, *, cache: PipelinedRedisCacheInterface, settings: SurfacesConfigInterface, clock: Clock, memo: BoundedTtlMemoInterface[str, str] | None = None, writes: SurfaceExecutorInterface | None = None, args: SurfaceArgsCodecInterface = SURFACE_ARGS, catalogue: SurfaceCatalogueInterface = CATALOGUE)`.
   `memo` defaults to `BoundedTtlMemo(settings.cache.memo_max_entries)` when
   `settings.cache.memo` is true, else no memo. `writes` defaults to a
   `SurfaceOperationHandler(adapter=cache, settings=settings, clock=clock)` (retries, bound).
2. `async execute(self, request) -> OperationOutcome`; the surface must be `cache` (else
   `ValueError`):
   - **`get`**: expired `start_by` → `EXPIRED` as the handler does. Memo hit → `OK` with the
     value, `attempts=0`. Miss → join the current batch and await its future:
     - the batch is a dict `key → list[Future]`; the first read of a turn schedules the flush
       with `loop.call_soon(...)` (no timer); every read arriving before the flush runs joins
       it; a batch never holds more than `settings.read_prefetch` distinct keys (a full batch
       flushes and a new one starts);
     - the flush records `generation_at_start`, calls
       `await cache.get_many_with_ttl(list(keys))` once, and resolves every future with its
       value; for each key whose value is not `None`, whose `len(value.encode()) <= settings.cache.memo_max_value_bytes`,
       whose PTTL is not `-2`, and when the generation has **not** moved, it fills the memo
       with `ttl_seconds=None` for PTTL `-1`, else `pttl / 1000`;
     - a `RedisError` (or any exception) fails every future of that batch; each read then
       returns `ERROR` with the detail (reads are never retried, §8).
   - **`set` / `delete`**: bump `self._generation`, remove the key from the memo, then run the
     write through `writes.execute(request)`; on `OK`, a `set` whose value fits is put in the
     memo with `ttl_seconds=ttl_seconds` (or none), and a `delete` leaves it absent. Return the
     write's outcome.
3. `stats(self) -> CacheLaneStats` (frozen dataclass: `memo_hits`, `memo_misses`, `batches`,
   `batched_reads`, `generation`), reset by `reset_stats()`; the meter reads and resets it
   per interval.
4. `src/vibey/infrastructure/surface_lanes/interfaces/cache_handler_interface.py`:
   `@runtime_checkable class CacheLaneHandlerInterface(SurfaceExecutorInterface, Protocol)`
   adding `stats` and `reset_stats`; exported. Registry: `CacheLaneHandlerInterface →` the real
   class over `PipelinedRedisCache(url="redis://fake", connector=InMemoryRedis().stream_connector())`
   (a `functools.partial` building fresh parts), in `REGISTRY` and `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/cache_handler.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/cache_handler_interface.py`; interfaces
  `__init__.py`; `tests/fakes/registry.py`.
- New `tests/infrastructure/surface_lanes/test_cache_handler.py`.

## Acceptance criteria
- [ ] 16 concurrent `get`s of distinct keys (gathered in one turn) cause one pipeline (`InMemoryRedis` saw one write of 32 commands); a single `get` also flushes in the same turn (no timer).
- [ ] A second `get` of a stored key is a memo hit that sends nothing to Valkey.
- [ ] A key set with `EX 1` is memoized with a TTL of 1 s and becomes a miss when the memo's clock passes it.
- [ ] A read whose flush started before a concurrent `set` of the same key is answered but **not** memoized (the generation moved); the next read goes to Valkey.
- [ ] `set` then `get` returns the new value from the memo; `delete` then `get` misses and returns `None`.
- [ ] A dropped Valkey connection fails every read of the batch with `error`, and the next batch reconnects.
- [ ] `memo = false` or `memo_max_entries = 0` sends every read to Valkey.
- [ ] 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_cache_handler.py` (no service; `InMemoryRedis(clock=…).stream_connector()`, `BoundedTtlMemo(…, clock=…)`, `FakeClock`):
- `test_concurrent_reads_share_one_pipeline`
- `test_a_lone_read_flushes_without_a_timer`
- `test_a_hit_touches_no_valkey`
- `test_the_memo_never_outlives_pttl`
- `test_a_read_racing_a_write_is_not_memoized`
- `test_set_and_delete_keep_the_memo_coherent`
- `test_a_failed_pipeline_fails_its_batch_only`
- `test_the_memo_can_be_disabled`
- `test_batches_are_capped_at_read_prefetch`
- `test_stats_count_hits_misses_and_batches`
- `test_handler_satisfies_its_interface`

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
- `CachePort.get_many` and RabbitMQ direct reply-to (held back until the measurement, ADR §10).
  Measuring (`surfaces-lane-meter`, `surfaces-bench`). CHANGELOG.md, docs/, ADRs, CLAUDE.md,
  AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or
  change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-pipelined-redis`, `surfaces-memo`, `surfaces-operation-handler`.
- **Shares a file with:** `tests/fakes/registry.py`.
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/` and `tests/infrastructure/cache/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - The default run needs no service: no Valkey.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
