## Title
feat(bench): a tracked, repeatable measurement of what a cache read costs through its lane, against Valkey

## Why
Draft ADR-0047 §10 (`specs/ADR-surface-lanes.md`, "The cache, honestly") measured today's Redis
paths on 2026-09-22 "ad hoc from the design session" and only **estimated** the queue paths: "no
broker was reachable". It owes a real measurement "(lane S32, `scripts/bench_surface_lanes.py`),
before lane S33 flips the default":
- **modes:** the direct adapter, `PipelinedRedisCache`, the queue with a memo hit, and the queue
  with a memo miss; p50, p95 and p99 latency and throughput;
- **load:** concurrency 1 and 16, 10 000 operations each after a warm-up;
- **images:** the pinned broker image and the pinned cache image — now **Valkey**, which the
  ADR's Decision says the §10 numbers are re-taken against (`surfaces-chart-valkey`);
- **machines:** once on the operator's laptop (macOS, the default paid OS) and once on a Linux
  node — here **Arch Linux**, the default sovereign OS (sub-doctrine 8.h: "every change is proven
  on both").

"The JSON is recorded in this record's evidence. The operator then decides, in writing." 8.f's
own text: the cache's cost "is measured and published with the design that carries this rule";
8.g and 10.f: measurements drive decisions and are published with them. The logic lives in a
class (tested); the script is its entry guard (ADR "non-negotiable 10").

## Required behaviour
1. **`src/vibey/infrastructure/surface_lanes/bench.py`**, `class SurfaceLaneBenchmark`:
   `__init__(self, *, cache_url: str, amqp: AmqpClientInterface, direct_cache: CachePort, pipelined: PipelinedRedisCacheInterface, clock: Callable[[], float] = time.perf_counter, settings: SurfacesConfig = SurfacesConfig())`.
   `async run(self, *, operations: int, warmup: int, concurrency: Sequence[int]) -> dict[str, object]`:
   - seeds one 64-byte value under a fixed key (the ADR's workload);
   - for each mode and each concurrency, runs `warmup` untimed gets, then `operations` timed gets
     issued by `concurrency` concurrent tasks, timing each get with `clock`;
   - `direct`: `direct_cache.get(key)`; `pipelined`: `pipelined.get(key)`;
     `queue-hit` and `queue-miss`: an in-process lane — `SurfaceLaneTopology.declare(cache)`, a
     `SurfaceRequestDispatcher` over a `CacheLaneHandler` (memo on for `hit`; `memo=False` for
     `miss`), consuming the read queue with `read_prefetch`, and a `SurfaceLaneClient` whose
     `QueuedCache.get(key)` is timed (the full caller → broker → lane → cache → broker → caller
     path; the memo is warmed by the warm-up for `hit`);
   - returns `{"measured_at": ISO UTC, "platform": platform.platform(), "machine": platform.machine(), "python": platform.python_version(), "cache_server": <"valkey_version" or "redis_version" from INFO server>, "operations": n, "warmup": n, "modes": {mode: {str(concurrency): {"p50_ms", "p95_ms", "p99_ms", "ops_per_second"}}}}`
     (nearest-rank percentiles, three decimals).
   The dispatcher's recorder is `BenchmarkRecorder` (in the same module, implementing
   `SurfaceLedgerRecorderInterface`, every method returning False): the benchmark's requests
   carry no project, so a real recorder would ledger nothing either, and the benchmark needs no
   database. The meter is a real `SurfaceLaneMeter` over a discarding logger.
   Interfaces `SurfaceLaneBenchmarkInterface` (and the recorder uses the existing one) in
   `surface_lanes/interfaces/bench_interface.py`.
2. **`scripts/bench_surface_lanes.py`** (new): `argparse` with `--cache-url` (required),
   `--amqp-url` (required), `--operations` (10000), `--warmup` (500), `--concurrency` (`1,16`),
   `--out` (a path; stdout when omitted). It builds the real `AmqpClient`, `RedisCacheAdapter`
   and `PipelinedRedisCache`, runs the benchmark, writes the JSON (indented, sorted keys), and
   closes everything. The `if __name__ == "__main__":` guard is its only module-level code, with
   a one-line reason comment. It never prints a password (URLs are redacted in any message).
3. **The measurement itself is operator evidence, not CI.** The lane's commit body records
   whether the lane ran it and where. The ADR's evidence (`surfaces-docs-wave`) holds the two
   JSON files, `docs/architecture/decisions/evidence/0047/bench-macos.json` and
   `docs/architecture/decisions/evidence/0047/bench-arch.json`, produced by the operator with the
   pinned `valkey/valkey` image
   (`deploy/helm/vibey/values.yaml` `surfaces.redis.image`) and the pinned
   `rabbitmq:4-management-alpine`.

## Where to change
- New `src/vibey/infrastructure/surface_lanes/bench.py`,
  `src/vibey/infrastructure/surface_lanes/interfaces/bench_interface.py`; interfaces
  `__init__.py`; new `scripts/bench_surface_lanes.py`.
- New `tests/infrastructure/surface_lanes/test_bench.py` and
  `tests/infrastructure/surface_lanes/test_bench_integration.py`.

## Acceptance criteria
- [ ] With no service (`InMemoryAmqpClient`, `InMemoryRedis` connectors for both cache clients, a stepping fake clock), `run(operations=20, warmup=2, concurrency=[1, 4])` returns all four modes at both concurrencies with every key above, and the fake clock's steps give exact percentiles.
- [ ] `queue-hit` served every timed read from the memo (the in-memory Valkey saw no GET after the warm-up); `queue-miss` sent every read to it.
- [ ] Integration (`amqp_url` and `cache_url` fixtures): `operations=200` produces positive numbers in every cell.
- [ ] `uv run python scripts/bench_surface_lanes.py --help` works; the script holds no logic outside the guard.
- [ ] 100% `infrastructure/` branch coverage; bandit is clean.

## Tests to write first (TDD)
`tests/infrastructure/surface_lanes/test_bench.py` (no service):
- `test_every_mode_and_concurrency_is_reported`
- `test_percentiles_follow_the_clock`
- `test_the_hit_mode_never_reaches_valkey_after_warmup`
- `test_the_miss_mode_always_reaches_valkey`
- `test_benchmark_satisfies_its_interface`
`tests/infrastructure/surface_lanes/test_bench_integration.py` (`amqp_url`, `cache_url`):
- `test_a_short_run_against_real_services`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey scripts/bench_surface_lanes.py
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/surface_lanes
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    # With both services (record in the commit body whether it ran, and paste the JSON):
    uv run python scripts/bench_surface_lanes.py --cache-url "$VIBEY_TEST_CACHE_URL" --amqp-url "$VIBEY_TEST_AMQP_URL" --operations 1000

## Out of scope
- Deciding whether the cost is acceptable (the operator's, in writing, ADR §10). Direct
  reply-to and `CachePort.get_many` (held back until this measurement exists). CHANGELOG.md,
  docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees (`surfaces-docs-wave`). Do not
  push, open PRs or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `surfaces-composition` (every lane part exists), `surfaces-chart-valkey` (the pinned Valkey image named in the evidence).
- **Must keep passing unchanged:** everything under `tests/infrastructure/surface_lanes/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Every new class has a `@runtime_checkable` Protocol in `surface_lanes/interfaces/`.
  - Substitute only at a declared seam; never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.
  - Evidence is bounded (10.f): report only numbers a run produced, name the machine and the images.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
