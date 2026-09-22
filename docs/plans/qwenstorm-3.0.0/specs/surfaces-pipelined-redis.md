## Title
feat(cache): PipelinedRedisCache keeps one asyncio connection to Valkey, authenticates once, and pipelines GET with PTTL

## Why
Draft ADR-0047 §10 (`specs/ADR-surface-lanes.md`, "The lane has its own connection") measured
today's `RedisCacheAdapter.get` shape — a new TCP connection, AUTH, SELECT, GET and close,
through `asyncio.to_thread` (`src/vibey/infrastructure/cache/redis.py:64-81`) — at 0.18 ms p50,
and one persistent asyncio connection at 0.08 ms, or 0.006 ms per GET when 16 are pipelined.
The cache lane therefore uses one persistent connection, authenticates and selects once, and
batches its reads into one pipeline of `GET` and `PTTL` (§10 point 3), so its memo never
outlives the server's own expiry (point 4). The server is **Valkey** (the operator's ruling of
2026-09-22, ADR "Decision" first paragraph), which speaks the Redis protocol unchanged.

The existing test seam is `fakes-sockets`' `InMemoryRedis`, a RESP peer over
`socket.socketpair()` with no port. This lane teaches it `PTTL` and an asyncio stream
connector, so the pipelined client is tested with no server. ADR-0047 lane S13. Stdlib only.

## Required behaviour
1. **`src/vibey/infrastructure/cache/pipelined_redis.py`** (new):
   - `class AsyncioStreamConnector`: `async open(self, host: str, port: int, *, timeout: float) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]`
     = `await asyncio.wait_for(asyncio.open_connection(host, port), timeout)`.
     `ASYNCIO_STREAMS: Final[StreamConnectorInterface] = AsyncioStreamConnector()`.
   - `class PipelinedRedisCache` (implements `PipelinedRedisCacheInterface`, hence `CachePort`):
     `__init__(self, *, url: str, timeout: float = 5.0, connector: StreamConnectorInterface = ASYNCIO_STREAMS)`.
     The URL is parsed exactly as `RedisCacheAdapter.__init__` does (`redis.py:54-62`), with the
     same `ValueError` text; `timeout <= 0` raises `ValueError("timeout must be positive")`.
   - The connection is opened lazily on first use, under an `asyncio.Lock` created on first
     use. On opening it sends `AUTH` when the URL has a password and `SELECT` when the db is not
     0, once, and keeps the reader and writer.
   - `async _pipeline(self, commands: Sequence[tuple[bytes, ...]]) -> list[object]`: under the
     lock, writes every command encoded as RESP arrays in one `writer.write`, `await
     writer.drain()`, then reads exactly one reply per command, all within
     `asyncio.wait_for(..., timeout)`. An error reply (`-...`) is collected, not raised, until
     every reply is read; then the first one raises `RedisError` (from `redis.py`) and the
     connection is kept. An `OSError`, `asyncio.TimeoutError`, `asyncio.IncompleteReadError`
     or an unparseable reply closes the connection (the next call reopens it) and raises
     `RedisError(f"redis pipeline failed: {exc}")` from it.
   - `get(key) -> str | None` (one `GET`), `set(key, value, ttl_seconds=None)` (`SET` with
     `EX` when given), `delete(key)` (`DEL`) — the `CachePort` surface, same semantics as
     `RedisCacheAdapter`.
   - `async get_many_with_ttl(self, keys: Sequence[str]) -> list[tuple[str | None, int]]`: one
     pipeline of `GET k1, PTTL k1, GET k2, PTTL k2, …`; returns `(value, pttl_ms)` per key in
     order. `PTTL` is `-2` for a missing key and `-1` for a key with no expiry. An empty `keys`
     sends nothing and returns `[]`.
   - `async close(self) -> None`: closes the writer and waits for it, ignoring errors;
     idempotent.
   - RESP encoding and parsing are private methods of the class (no module functions).
2. **`src/vibey/infrastructure/cache/interfaces/pipelined_redis_interface.py`** (new):
   `@runtime_checkable class PipelinedRedisCacheInterface(CachePort, Protocol)` adding
   `get_many_with_ttl` and `close`; `@runtime_checkable class StreamConnectorInterface(Protocol)`
   with `open`. Export both from `src/vibey/infrastructure/cache/interfaces/__init__.py`.
3. **The fake** (`tests/fakes/sockets.py`, `InMemoryRedis` from `fakes-sockets`):
   - it tracks expiries set by `SET … EX n` against an injectable
     `clock: Callable[[], float] = time.monotonic` constructor keyword, and answers `PTTL` with
     `-2`, `-1` or the remaining milliseconds (an expired key is gone for `GET` too);
   - it serves every command it has read before answering, in order, so a pipeline of N
     commands gets N replies;
   - `stream_connector() -> StreamConnectorInterface`: each `open()` makes a new
     `socket.socketpair()`, serves one end on a thread exactly as `connector()` does, and
     returns `await asyncio.open_connection(sock=other_end)`. It appends `(host, port)` to a new
     `opened: list[tuple[str, int]]`, so a test can prove one connection served many calls;
   - if it does not already record received commands, add `commands: list[tuple[str, ...]]`.
4. **Registry.** In `tests/fakes/registry.py`, register
   `StreamConnectorInterface → InMemoryRedis().stream_connector` and add
   `StreamConnectorInterface` to `DRIVER_SEAMS`.

## Where to change
- New `src/vibey/infrastructure/cache/pipelined_redis.py`,
  `src/vibey/infrastructure/cache/interfaces/pipelined_redis_interface.py`;
  `src/vibey/infrastructure/cache/interfaces/__init__.py` (exports).
- `tests/fakes/sockets.py`, `tests/fakes/registry.py`.
- New `tests/infrastructure/cache/__init__.py` (provenance line only, if missing),
  `tests/infrastructure/cache/test_pipelined_redis.py`,
  `tests/infrastructure/cache/test_pipelined_redis_integration.py`.

## Acceptance criteria
- [ ] Ten `get` calls open one connection (`len(fake.opened) == 1`) and send `AUTH` and `SELECT` once.
- [ ] `get_many_with_ttl(["a", "b", "c"])` sends six commands in one write and returns `(value, -1)` for a key without expiry, `(None, -2)` for a missing key and a positive TTL for a key set with `EX`.
- [ ] An error reply for one command in a pipeline raises `RedisError` after the whole pipeline is read, and the next call reuses the connection.
- [ ] A dropped connection raises `RedisError`, and the next call reopens (`len(fake.opened) == 2`).
- [ ] Integration (`VIBEY_TEST_CACHE_URL=redis://…` to a Valkey server): `PTTL` is `-2` for a missing key and `-1` for a key with no expiry (the ADR's *Verification owed* item for S13), and a pipeline round-trips.
- [ ] `isinstance(PipelinedRedisCache(url="redis://h"), CachePort)`; the fakes parity test passes; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/cache/test_pipelined_redis.py` (no service; `InMemoryRedis(password=...).stream_connector()`):
- `test_one_connection_serves_many_calls_and_authenticates_once`
- `test_get_many_with_ttl_pipelines_get_and_pttl`
- `test_pttl_reports_missing_and_persistent_keys`
- `test_an_error_reply_is_raised_after_the_pipeline_is_drained`
- `test_a_dropped_connection_reopens_on_the_next_call`
- `test_url_and_timeout_are_validated`
- `test_set_with_ttl_and_delete`
- `test_close_is_idempotent`
`tests/infrastructure/cache/test_pipelined_redis_integration.py` (`@pytest.mark.integration`, skipped without `VIBEY_TEST_CACHE_URL`):
- `test_pttl_semantics_against_valkey`
- `test_pipeline_round_trip_against_valkey`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/cache tests/fakes tests/meta tests/infrastructure/test_sovereign_surfaces.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Replacing `RedisCacheAdapter` for `direct` transport (it stays). The memo, batching and
  generations (`surfaces-cache-handler`). CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md,
  GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not push, open PRs or change
  remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-sockets` (`InMemoryRedis`, `RedisError`'s seam), `fakes-registry`.
- **Shares a file with:** `tests/fakes/sockets.py` (extend `InMemoryRedis`; keep `connector()` working), `tests/fakes/registry.py` (append).
- **Must keep passing unchanged:** `tests/fakes/test_fake_sockets.py`, the Redis tests in `tests/infrastructure/test_sovereign_surfaces.py`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file. Change existing files with `edit_file` or a checked replacement; add tests in new files.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol beside it.
  - Substitute only at a declared seam (`connector=`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`. A fake under `tests/fakes/` never uses `unittest.mock`.
  - The default run needs no service: no Valkey, no loopback port.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
