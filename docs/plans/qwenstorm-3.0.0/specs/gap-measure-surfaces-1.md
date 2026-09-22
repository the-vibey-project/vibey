## Title
feat(measure): a surface meter wraps any surface port and summarizes each operation's calls per period

## Why
Sub-doctrine 8.g (`src/vibey_tools/gh/docs/doctrines.md:316-324`) measures every surface. The
twelve sovereign surface ports (`src/vibey/application/interfaces/{blob,bus,cache,config_store,
docs,email,files,messaging,secrets,siem,sms,tracker}.py`, every member an `async def`) record
nothing today. Writing one ledger event per call would put a database append on every cache read,
whose whole budget is milliseconds (ADR-0047 §10, `specs/ADR-surface-lanes.md:267-324`), so the
meter keeps each operation's call latencies in memory and states them once per `[measure]`
period as a latency summary (`LatencySummary`, lane `gap-measure-domain`): count, errors,
throughput and p50/p95/p99/max. It is a `MeasurementSource` (lane `gap-measure-port`), collected
by the ticker (lane `gap-measure-ticker`).

The wrapper must still satisfy the port. Python 3.12's `isinstance` against a
`runtime_checkable` Protocol looks attributes up with `inspect.getattr_static`, which never calls
`__getattr__`, so a delegating proxy would fail `isinstance(port, CachePort)`. The meter
therefore builds, once per Protocol, a class whose methods are the Protocol's own members.

## Required behaviour
1. New `src/vibey/infrastructure/measure/surface_meter.py`:
   - `class MeasuredSurface`: `__init__(self, surface: str, inner: object, meter:
     SurfaceMeterInterface)`; properties `surface -> str` and `inner -> object`. It declares no
     port method itself.
   - `class SurfaceMeter`: `__init__(self, *, clock: Clock, monotonic: Callable[[], float] =
     time.monotonic, instance: str = "", ids: Callable[[], UUID] = uuid4)`; `name` property
     returns `"surfaces"`.
     - `wrap(self, surface: str, port: P, protocol: type[P]) -> P` (`P = TypeVar("P")`): the
       members are the non-underscore names in `vars(c)` for every `c` in `protocol.__mro__` with
       `c.__dict__.get("_is_protocol")`, sorted; any member that is not a coroutine function
       (`inspect.iscoroutinefunction`) raises `TypeError(f"{protocol.__name__}.{name} is not
       async; the surface meter times async operations only")`. The class
       `type(f"Measured{protocol.__name__}", (MeasuredSurface,), namespace)` is built once per
       Protocol and cached; `namespace[name]` is an `async def` that reads `start =
       self._meter.monotonic()`, awaits `getattr(self.inner, name)(*args, **kwargs)`, and calls
       `meter.observe(surface, name, monotonic() - start, failed=…)` — `failed=True` and re-raise
       on any `BaseException`, `failed=False` otherwise, returning the result. Returns
       `cast(P, cls(surface, port, self))`.
     - `observe(self, surface: str, operation: str, seconds: float, *, failed: bool) -> None`
       appends to the window of `(surface, operation)`.
     - `async def collect(self) -> tuple[Measurement, ...]`: `now = clock.now()`; for every
       `(surface, operation)` observed since the last collect, sorted: subject
       `MeasurementSubject(SubjectKind.SURFACE, f"{surface}.{operation}")`, `started_at` = when
       this window opened (construction, or the previous collect), `ended_at = now`, readings
       `LATENCY_SUMMARY.readings(samples, errors=errors, window_seconds=(now -
       opened).total_seconds())`, outcome `OK` when `errors == 0` else `FAILED` with detail
       `f"{errors} of {count} calls failed"`, `instance`. Then the windows are cleared and the
       next opens at `now`. An operation not called in the window records nothing.
2. New `src/vibey/infrastructure/measure/interfaces/surface_meter_interface.py`:
   `SurfaceMeterInterface` (`name`, `wrap`, `observe`, `collect`, and a `monotonic` property
   returning the time function) and `MeasuredSurfaceInterface` (`surface`, `inner`).

## Where to change
- New `src/vibey/infrastructure/measure/surface_meter.py` and its interface file.
- New `tests/infrastructure/measure/test_surface_meter.py`. Wrap the real in-memory surfaces
  (`vibey.infrastructure.cache.in_memory.InMemoryCache`, `…bus.in_memory.InMemoryBus`), drive
  time with `FakeClock` (`tests/fakes/system.py`) and a plain counter function for `monotonic`.

## Acceptance criteria
- [ ] `meter.wrap("cache", InMemoryCache(), CachePort)` is an instance of `CachePort` and of
      `MeasuredSurface`, and `await wrapped.set("k", "v")` then `await wrapped.get("k")` returns
      `"v"`.
- [ ] Two `get`s of 0.2 s and 0.4 s and one `set` of 0.1 s, collected 10 s after construction,
      give `cache.get` (count 2, errors 0, throughput 0.2, p50 0.2, max 0.4, outcome `ok`) and
      `cache.set` (count 1); a second collect with no calls returns `()`.
- [ ] A call that raises is counted in `errors`, re-raised unchanged, and makes the window
      `failed` with detail `"1 of 1 calls failed"`.
- [ ] Wrapping a Protocol with a sync member raises `TypeError`; two wraps of `CachePort`
      share one generated class.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/measure/test_surface_meter.py`:
- `test_a_wrapped_surface_still_satisfies_its_port_and_works`
- `test_collect_summarizes_each_operation_and_resets_the_window`
- `test_a_failing_call_is_counted_and_reraised`
- `test_only_async_protocols_can_be_wrapped`
- `test_the_generated_class_is_built_once_per_protocol`
- `test_every_surface_port_can_be_wrapped` (parametrized over the twelve ports and their
  `in_memory` classes, `isinstance` each wrap)
- `test_the_meter_satisfies_its_interfaces` (`MeasurementSource`, `SurfaceMeterInterface`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/infrastructure/measure
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wrapping the ports at the composition root (`gap-measure-surfaces-2`); the surface lanes of
  ADR-0047 (they are wrapped at the root like any other port once they compose).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(measure): a surface meter wraps any surface port and summarizes each operation's calls per period`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port`, `gap-measure-ledger-sink` (the `infrastructure/measure/`
  package), `fakes-observability`.
- **Must keep passing unchanged:** every surface adapter test and the protected tests.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
